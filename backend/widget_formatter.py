"""
Widget Formatter Utility

This module provides utility functions to format data for the frontend widget system.
It detects appropriate widget types based on data structure and creates standardized
response formats for different widget types.
"""

import datetime
import json
from typing import Dict, List, Any, Union, Optional
import re
from json_encoder import CustomJsonEncoder

class DateTimeEncoder(CustomJsonEncoder):
    """JSON encoder that handles datetime objects by converting to ISO format."""
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)

class WidgetFormatter:
    """
    Utility class to format data for the frontend widget system.
    
    This class detects the appropriate widget type based on data structure
    and formats the data according to the widget's expected format.
    """
    
    @staticmethod
    def format_response(
        data: Any, 
        query: str = "", 
        widget_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        fallback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format data for frontend widget display.
        
        Args:
            data: The data to format (typically from SQL query)
            query: The original user query for context
            widget_type: Override widget type detection if provided
            metadata: Additional configuration for the widget
            fallback: Text fallback for the widget
            
        Returns:
            Dict with widget type, data, metadata, and fallback
        """
        # Auto-detect widget type if not provided
        if widget_type is None:
            widget_type = WidgetFormatter.detect_widget_type(data, query)
            
        # Format based on detected widget type
        formatter_method = getattr(
            WidgetFormatter, 
            f'format_as_{widget_type}', 
            WidgetFormatter.format_as_text
        )
        
        # Call the appropriate formatter method
        formatted_data = formatter_method(data, query, metadata)
        
        # Include a fallback if not already present
        if 'fallback' not in formatted_data and fallback is not None:
            formatted_data['fallback'] = fallback
        elif 'fallback' not in formatted_data:
            # Generate fallback if not provided
            formatted_data['fallback'] = WidgetFormatter.generate_fallback(
                data, 
                widget_type,
                formatted_data.get('data', {})
            )
            
        return formatted_data
    
    @staticmethod
    def detect_widget_type(data: Any, query: str = "") -> str:
        """
        Detect the appropriate widget type based on data structure and query.

        Args:
            data: The data to analyze (typically from SQL query results).
            query: The original user query for context.

        Returns:
            String widget type identifier.
        """
        query_lower = query.lower()

        # 1. Prioritize Confirmation Widgets (query-based intent)
        confirmation_patterns = [
            r'\b(confirm|are you sure|proceed|verify|approve)\b',
            r'\b(delete|remove|drop)\b.*\?',
            r'\b(continue|go ahead)\b.*\?'
        ]
        for pattern in confirmation_patterns:
            if re.search(pattern, query_lower):
                return 'confirmation'
        
        # 2. Prioritize Options Widgets (query-based intent or data structure for options)
        option_patterns = [
            r'\b(choose|select|pick|option|which|what)\b.*\?',
            r'\bwould you like\b',
            r'\bdo you prefer\b'
        ]
        for pattern in option_patterns:
            if re.search(pattern, query_lower):
                return 'options'
        
        # If the data is specifically formatted as a dictionary with an 'options' key for a quick options widget
        if isinstance(data, dict) and 'options' in data and isinstance(data['options'], list) and data['options']:
            return 'options'
        
        # 3. Analyze data structure for SQL results or list of records
        if isinstance(data, list):
            # Empty results indicate no data, default to text
            if not data:
                return 'text'
            
            # Check if all items in the list are dictionaries (typically rows from a DB query)
            if not all(isinstance(row, dict) for row in data):
                return 'text' # If not uniform dictionaries, can't be table/agg/comparison reliably

            # Extract column names from the first row to determine structure
            first_row_keys = list(data[0].keys())
            num_columns = len(first_row_keys)

            # Check for potential Aggregation Widget
            # An aggregation is often a single row with one or two columns (e.g., 'COUNT(*)', 'total_sales')
            # Or multiple rows that fit an aggregation-like pattern if the query explicitly asks for aggregation.
            aggregation_keywords = r'\b(count|sum|avg|min|max|total|average)\b'
            is_aggregation_query = re.search(aggregation_keywords, query_lower)

            if len(data) == 1 and num_columns >= 1: # Single row result
                # If it's a single column and query has aggregation keywords, strongly suggest aggregation
                if num_columns == 1 and is_aggregation_query:
                    return 'aggregation'
                # If two columns, one might be a label and the other a value (e.g., 'status: 5')
                if num_columns == 2 and is_aggregation_query:
                    # Check if one of the columns is numeric and the other string-like
                    val1 = data[0][first_row_keys[0]]
                    val2 = data[0][first_row_keys[1]]
                    if (isinstance(val1, (int, float, type(None))) and isinstance(val2, str)) or \
                       (isinstance(val2, (int, float, type(None))) and isinstance(val1, str)):
                        return 'aggregation'
                # If it's just one value, assume aggregation
                if (num_columns == 1 and isinstance(data[0][first_row_keys[0]], (int, float, type(None)))):
                    return 'aggregation'

            # Check for potential Comparison Widget
            # Comparison widgets usually involve multiple rows of data, comparing values across categories.
            # Look for explicit comparison keywords in the query or a suitable data structure.
            comparison_keywords = r'\b(compare|vs|versus|breakdown|distribution|top ancient civilizations|population by country)\b'
            is_comparison_query = re.search(comparison_keywords, query_lower)

            if len(data) > 1 and num_columns >= 2:
                # If the query explicitly asks for comparison
                if is_comparison_query:
                    # Ensure at least one numeric column exists for comparison
                    if any(isinstance(data[0][key], (int, float, type(None))) and key not in ['id', 'name', 'label'] for key in first_row_keys):
                        return 'comparison'
                
                # Heuristic: if there are 2 columns, one string and one numeric, it's often a comparison
                if num_columns == 2:
                    col1_is_numeric = isinstance(data[0][first_row_keys[0]], (int, float, type(None)))
                    col2_is_numeric = isinstance(data[0][first_row_keys[1]], (int, float, type(None)))
                    col1_is_string = isinstance(data[0][first_row_keys[0]], str)
                    col2_is_string = isinstance(data[0][first_row_keys[1]], str)

                    if (col1_is_string and col2_is_numeric) or (col1_is_numeric and col2_is_string):
                        return 'comparison'
        
            # 4. Default to Table Widget for multi-row dictionary data not caught by above
            return 'table'
            
        # 5. Default to Text Widget for any other data type (string, int, float, or unhandled dicts)
        return 'text'
    
    @staticmethod
    def format_as_text(
        data: Any, 
        query: str = "", 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as a text widget."""
        if metadata is None:
            metadata = {}
            
        # Convert data to a formatted string if it's not already a string
        if not isinstance(data, str):
            if isinstance(data, (dict, list)):
                text = json.dumps(data, indent=2, cls=DateTimeEncoder)
            else:
                text = str(data)
        else:
            text = data
            
        return {
            'type': 'text',
            'data': {
                'text': text
            },
            'metadata': metadata
        }
    
    @staticmethod
    def format_as_table(
        data: List[Dict[str, Any]],
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as a table widget."""
        if metadata is None:
            metadata = {}
            
        if not isinstance(data, list) or not data:
            return WidgetFormatter.format_as_text("No data available")
            
        # Extract column names from first row
        columns = list(data[0].keys())
        
        return {
            'type': 'table',
            'data': {
                'columns': columns,
                'rows': data
            },
            'metadata': {
                'sortable': True,
                'pagination': {
                    'enabled': len(data) > 10,
                    'pageSize': 10
                },
                'title': WidgetFormatter._extract_table_title(query),
                **metadata
            },
            'fallback': WidgetFormatter._generate_table_fallback(data, columns)
        }
    
    @staticmethod
    def format_as_aggregation(
        data: Union[List[Dict[str, Any]], Dict[str, Any], int, float],
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as an aggregation widget."""
        if metadata is None:
            metadata = {}
            
        # Extract value and label from different data formats
        value = None
        label = ""
        
        # Case 1: List with a single dict (typical SQL aggregation result)
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            # The dict should have 1-2 keys (typically the aggregation function and value)
            if len(data[0]) >= 1:
                keys = list(data[0].keys())
                value = list(data[0].values())[0]
                label = keys[0]
                
        # Case 2: Single dict with explicit value and label keys
        elif isinstance(data, dict) and 'value' in data and 'label' in data:
            # Special case for our numerical extraction format
            value = data['value']
            label = data['label']
        # Case 3: Single dict with any label-value pair
        elif isinstance(data, dict) and len(data) >= 1:
            keys = list(data.keys())
            value = data[keys[0]]
            label = keys[0]
            
        # Case 3: Just a number
        elif isinstance(data, (int, float)):
            value = data
            
            # Try to extract a meaningful label from the query
            label = WidgetFormatter._extract_aggregation_label(query)
            
        # Default case: use text widget as fallback
        if value is None:
            return WidgetFormatter.format_as_text(data)
            
        # Detect if this is a count, average, etc.
        value_type = WidgetFormatter._detect_aggregation_type(label, query)
        
        # Format label if not already user-friendly
        if label and not label.istitle() and '_' in label:
            label = label.replace('_', ' ').title()
            
        return {
            'type': 'aggregation',
            'data': {
                'value': value,
                'label': label,
                'unit': metadata.get('unit', '')
            },
            'metadata': {
                'format': value_type.get('format', 'number'),
                'precision': 0 if isinstance(value, int) else 2,
                'size': 'medium',
                **metadata
            },
            'fallback': f"{label}: {value}"
        }
    
    @staticmethod
    def format_as_comparison(
        data: List[Dict[str, Any]],
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as a comparison widget."""
        if metadata is None:
            metadata = {}
            
        if not isinstance(data, list) or len(data) < 2:
            return WidgetFormatter.format_as_text(data)
            
        # Identify label and value columns
        # Typically one column is a category/label, the other is a numeric value
        columns = list(data[0].keys())
        if len(columns) < 2:
            return WidgetFormatter.format_as_text(data)
            
        # Find which column is likely to be the value (numeric)
        # and which is the label (string/category)
        label_col = None
        value_col = None
        
        for col in columns:
            # Check the first value type
            val = data[0][col]
            if isinstance(val, (int, float)):
                value_col = col
            elif isinstance(val, str):
                label_col = col
                
        # If we couldn't determine, use first column as label, second as value
        if label_col is None and value_col is None:
            label_col, value_col = columns[0], columns[1]
        elif label_col is None:
            # Find a non-value column for label
            for col in columns:
                if col != value_col:
                    label_col = col
                    break
            # If still None, use the first column
            if label_col is None:
                label_col = columns[0]
        elif value_col is None:
            # Find a non-label column for value
            for col in columns:
                if col != label_col:
                    value_col = col
                    break
            # If still None, use the second column
            if value_col is None and len(columns) > 1:
                value_col = columns[1]
            else:
                return WidgetFormatter.format_as_text(data)
                
        # Extract title from query or column names
        title = WidgetFormatter._extract_comparison_title(query, label_col, value_col)
        
        # Format the data for the comparison widget
        comparison_items = []
        for row in data:
            comparison_items.append({
                'label': str(row[label_col]),
                'value': float(row[value_col]) if isinstance(row[value_col], (int, float)) else 0
            })
            
        # Determine best chart type
        chart_type = 'bar'  # Default
        if len(comparison_items) > 8:
            chart_type = 'horizontal'  # Horizontal bars better for many items
        
        return {
            'type': 'comparison',
            'data': {
                'title': title,
                'items': comparison_items
            },
            'metadata': {
                'chartType': chart_type,
                'sortBy': 'value',
                'sortDirection': 'desc',
                **metadata
            },
            'fallback': WidgetFormatter._generate_comparison_fallback(comparison_items, title)
        }
    
    @staticmethod
    def format_as_confirmation(
        data: Any,
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as a confirmation widget."""
        if metadata is None:
            metadata = {}
            
        # Extract action details from query
        action_details = WidgetFormatter._extract_confirmation_details(query)
        
        # Allow override of extracted details
        if isinstance(data, dict):
            message = data.get('message', action_details['message'])
            action = data.get('action', action_details['action'])
            danger = data.get('danger', action_details['danger'])
            target = data.get('target', None)
            details = data.get('details', '')
            confirm_text = data.get('confirmText', 'Confirm')
            cancel_text = data.get('cancelText', 'Cancel')
        else:
            message = action_details['message']
            action = action_details['action']
            danger = action_details['danger']
            target = None
            details = ''
            confirm_text = 'Confirm'
            cancel_text = 'Cancel'
            
        return {
            'type': 'confirmation',
            'data': {
                'message': message,
                'details': details,
                'confirmText': confirm_text,
                'cancelText': cancel_text,
                'action': action,
                'target': target,
                'danger': danger
            },
            'metadata': metadata,
            'fallback': f"{message}\n{details}\n\nPlease confirm this action."
        }
    
    @staticmethod
    def format_as_options(
        data: Union[List[Dict[str, Any]], List[str], Dict[str, Any]],
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format data as an options widget."""
        if metadata is None:
            metadata = {}
            
        # Extract question from query
        question = WidgetFormatter._extract_question(query)
        
        # Process options based on data format
        options = []
        
        # Case 1: List of dicts with id/label already structured
        if (isinstance(data, list) and data and isinstance(data[0], dict) 
                and 'id' in data[0] and 'label' in data[0]):
            options = data
            
        # Case 2: List of strings
        elif isinstance(data, list) and data and isinstance(data[0], str):
            options = [
                {'id': str(i), 'label': item}
                for i, item in enumerate(data)
            ]
            
        # Case 3: Dict with keys as ids and values as labels
        elif isinstance(data, dict):
            options = [
                {'id': str(k), 'label': v if isinstance(v, str) else str(v)}
                for k, v in data.items()
            ]
            
        # Case 4: Dict with 'options' key
        elif isinstance(data, dict) and 'options' in data:
            if isinstance(data['options'], list):
                # If options is a list of dicts with id/label
                if data['options'] and isinstance(data['options'][0], dict):
                    if 'id' in data['options'][0] and 'label' in data['options'][0]:
                        options = data['options']
                    else:
                        # Convert generic dicts to option format
                        options = []
                        for i, opt in enumerate(data['options']):
                            option = {'id': str(i)}
                            # Try to find a good label field
                            for key in ['name', 'title', 'label', 'value']:
                                if key in opt:
                                    option['label'] = opt[key]
                                    break
                            else:
                                # If no good label field, just use the first value
                                if opt:
                                    option['label'] = str(list(opt.values())[0])
                                else:
                                    option['label'] = f"Option {i+1}"
                                    
                            # Add description if available
                            if 'description' in opt:
                                option['description'] = opt['description']
                                
                            options.append(option)
                # If options is a list of strings
                elif data['options'] and isinstance(data['options'][0], str):
                    options = [
                        {'id': str(i), 'label': item}
                        for i, item in enumerate(data['options'])
                    ]
            
            # Use question from data if provided
            if 'question' in data and data['question']:
                question = data['question']
                
        # If we couldn't process the options, return text widget
        if not options:
            return WidgetFormatter.format_as_text(
                data, 
                query=f"No valid options found for query: {query}"
            )
        
        # Determine best display style based on number and length of options
        display_style = 'buttons'  # Default
        
        if len(options) > 5:
            # Many options - use cards or dropdown
            if any(len(opt.get('label', '')) > 20 for opt in options):
                display_style = 'cards'
            else:
                display_style = 'dropdown'
         
        # If any option has a description, use cards
        if any('description' in opt for opt in options):
            display_style = 'cards'
            
        return {
            'type': 'options',
            'data': {
                'question': question,
                'options': options,
                'requireConfirmation': len(options) > 1
            },
            'metadata': {
                'displayStyle': display_style,
                'enableSearch': len(options) > 10,
                **metadata
            },
            'fallback': WidgetFormatter._generate_options_fallback(options, question)
        }
    
    # Helper methods for extracting context
    
    @staticmethod
    def _extract_table_title(query: str) -> str:
        """Extract a title for a table from the query."""
        # Look for phrases like "Show me X" or "List all X"
        match = re.search(r'show\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+from|\s+where|\s+for|\?|$)', query, re.I)
        if match:
            return match.group(1).capitalize()
            
        match = re.search(r'list\s+(?:all\s+)?(?:the\s+)?(.+?)(?:\s+from|\s+where|\s+for|\?|$)', query, re.I)
        if match:
            return match.group(1).capitalize()
            
        match = re.search(r'get\s+(?:all\s+)?(?:the\s+)?(.+?)(?:\s+from|\s+where|\s+for|\?|$)', query, re.I)
        if match:
            return match.group(1).capitalize()
            
        # Default to a generic title
        return "Query Results"
    
    @staticmethod
    def _extract_aggregation_label(query: str) -> str:
        """Extract a label for an aggregation from the query."""
        # Look for aggregation functions in the query
        for agg_func in ['count', 'sum', 'average', 'avg', 'minimum', 'min', 'maximum', 'max']:
            match = re.search(f'{agg_func}\\s+(?:of\\s+)?(?:the\\s+)?(.+?)(?:\\s+from|\\s+in|\\s+where|\\?|$)', 
                             query, re.I)
            if match:
                return f"{agg_func.title()} of {match.group(1)}"
                
        # Look for "how many X" pattern
        match = re.search(r'how\s+many\s+(.+?)(?:\s+are|\s+do|\s+does|\s+in|\s+from|\s+where|\?|$)',
                         query, re.I)
        if match:
            return f"Count of {match.group(1)}"
            
        # Look for "what is the total X" pattern
        match = re.search(r'what\s+is\s+the\s+total\s+(.+?)(?:\s+from|\s+in|\s+where|\?|$)',
                         query, re.I)
        if match:
            return f"Total {match.group(1)}"
            
        # Default
        return "Value"
    
    @staticmethod
    def _detect_aggregation_type(label: str, query: str) -> Dict[str, str]:
        """Detect the type of aggregation and appropriate formatting."""
        label_lower = label.lower()
        query_lower = query.lower()
        
        # Currency detection
        currency_patterns = [
            'revenue', 'sales', 'income', 'price', 'cost', 'expense', 
            'profit', 'payment', 'salary', 'budget', 'amount', '$', '€', '£', 'dollar', 'euro'
        ]
        for pattern in currency_patterns:
            if pattern in label_lower or pattern in query_lower:
                return {'type': 'currency', 'format': 'currency'}
                
        # Percentage detection
        percentage_patterns = [
            'percent', 'ratio', 'rate', 'share', 'portion', 'proportion', '%'
        ]
        for pattern in percentage_patterns:
            if pattern in label_lower or pattern in query_lower:
                return {'type': 'percentage', 'format': 'percentage'}
                
        # Count detection
        count_patterns = [
            'count', 'number of', 'how many', 'quantity', 'total number'
        ]
        for pattern in count_patterns:
            if pattern in label_lower or pattern in query_lower:
                return {'type': 'count', 'format': 'number'}
                
        # Average detection
        avg_patterns = [
            'average', 'avg', 'mean'
        ]
        for pattern in avg_patterns:
            if pattern in label_lower or pattern in query_lower:
                return {'type': 'average', 'format': 'decimal'}
                
        # Default to generic number
        return {'type': 'value', 'format': 'number'}
    
    @staticmethod
    def _extract_comparison_title(query: str, label_col: str, value_col: str) -> str:
        """Extract a title for a comparison chart from the query and columns."""
        # Try to construct a title from the query
        compare_patterns = [
            r'compare\s+(?:the\s+)?(.+?)(?:\s+by|\s+across|\s+between|\s+from|\s+in|\s+where|\?|$)',
            r'show\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+by|\s+across|\s+between|\s+from|\s+in|\s+where|\?|$)'
        ]
        
        for pattern in compare_patterns:
            match = re.search(pattern, query, re.I)
            if match:
                return f"{match.group(1).capitalize()} by {label_col.replace('_', ' ').title()}"
                
        # If no match, use the column names
        label_col_formatted = label_col.replace('_', ' ').title()
        value_col_formatted = value_col.replace('_', ' ').title()
        
        return f"{value_col_formatted} by {label_col_formatted}"
    
    @staticmethod
    def _extract_confirmation_details(query: str) -> Dict[str, Any]:
        """Extract action details from a confirmation query."""
        # Default values
        details = {
            'message': 'Are you sure you want to proceed?',
            'action': 'confirm_action',
            'danger': False
        }
        
        # Check for potential confirmation intents
        # Delete/Remove
        if re.search(r'\b(delete|remove|drop)\b', query, re.I):
            details['message'] = 'Are you sure you want to delete this item?'
            details['action'] = 'delete'
            details['danger'] = True
            
            # Check what's being deleted
            match = re.search(r'\b(delete|remove|drop)\s+(?:the\s+)?(.+?)(?:\s+from|\s+where|\?|$)', query, re.I)
            if match:
                details['message'] = f"Are you sure you want to delete {match.group(2)}?"
                
        # Update/Modify
        elif re.search(r'\b(update|change|modify|edit)\b', query, re.I):
            details['message'] = 'Are you sure you want to update this item?'
            details['action'] = 'update'
            
            # Check what's being updated
            match = re.search(r'\b(update|change|modify|edit)\s+(?:the\s+)?(.+?)(?:\s+to|\s+with|\s+where|\?|$)', 
                             query, re.I)
            if match:
                details['message'] = f"Are you sure you want to update {match.group(2)}?"
                
        # Create/Add
        elif re.search(r'\b(create|add|insert|new)\b', query, re.I):
            details['message'] = 'Are you sure you want to create this item?'
            details['action'] = 'create'
            
            # Check what's being created
            match = re.search(r'\b(create|add|insert|new)\s+(?:a\s+)?(?:new\s+)?(.+?)(?:\s+with|\s+where|\?|$)', 
                             query, re.I)
            if match:
                details['message'] = f"Are you sure you want to create a new {match.group(2)}?"
                
        # Process/Execute
        elif re.search(r'\b(process|execute|run|start)\b', query, re.I):
            details['message'] = 'Are you sure you want to proceed with this operation?'
            details['action'] = 'process'
            
            # Check what's being processed
            match = re.search(r'\b(process|execute|run|start)\s+(?:the\s+)?(.+?)(?:\s+with|\s+where|\?|$)', 
                             query, re.I)
            if match:
                details['message'] = f"Are you sure you want to {match.group(1)} {match.group(2)}?"
                
        return details
    
    @staticmethod
    def _extract_question(query: str) -> str:
        """Extract a question from the query string."""
        # If query is already a question, return it
        if query.strip().endswith('?'):
            return query.strip()
            
        # Look for question patterns
        question_patterns = [
            r'(which|what|how|where|who|when).+?\?',
            r'(can|could|would|should|do|does|is|are|will).+?\?'
        ]
        
        for pattern in question_patterns:
            match = re.search(pattern, query, re.I)
            if match:
                return match.group(0)
                
        # Look for "choose/select" patterns
        choose_patterns = [
            r'(choose|select|pick)\s+(?:from\s+)?(?:the\s+)?(.+?)(?:\s+from|\s+in|\s+where|\?|$)',
        ]
        
        for pattern in choose_patterns:
            match = re.search(pattern, query, re.I)
            if match:
                return f"Please {match.group(1)} from the following {match.group(2)}:"
                
        # Default to a generic question
        return "Please select an option:"
    
    # Fallback generation methods
    
    @staticmethod
    def generate_fallback(data: Any, widget_type: str, formatted_data: Dict[str, Any]) -> str:
        """Generate a text fallback for a widget."""
        # Default implementation based on widget type
        method_name = f'_generate_{widget_type}_fallback'
        method = getattr(WidgetFormatter, method_name, None)
        
        if method and callable(method):
            args = []
            if widget_type == 'table' and 'columns' in formatted_data and 'rows' in formatted_data:
                args = [formatted_data['rows'], formatted_data['columns']]
            elif widget_type == 'comparison' and 'items' in formatted_data and 'title' in formatted_data:
                args = [formatted_data['items'], formatted_data['title']]
            elif widget_type == 'options' and 'options' in formatted_data and 'question' in formatted_data:
                args = [formatted_data['options'], formatted_data['question']]
            
            if args:
                return method(*args)
        
        # Default fallback: convert data to string
        if isinstance(data, (dict, list)):
            return json.dumps(data, indent=2, cls=DateTimeEncoder)
        else:
            return str(data)
    
    @staticmethod
    def _generate_table_fallback(data: List[Dict[str, Any]], columns: List[str]) -> str:
        """Generate a text fallback for a table widget."""
        if not data or not columns:
            return "No data available."
            
        result = []
        
        # Create header row
        header = ' | '.join(columns)
        sep = '-' * len(header)
        
        result.append(header)
        result.append(sep)
        
        # Add data rows
        for row in data[:10]:  # Limit to first 10 rows in the fallback
            row_values = []
            for col in columns:
                val = row.get(col, '')
                if isinstance(val, (dict, list)):
                    val = str(val)
                row_values.append(str(val))
            result.append(' | '.join(row_values))
            
        # Add indication if there are more rows
        if len(data) > 10:
            result.append(f"\n... and {len(data) - 10} more rows.")
            
        return '\n'.join(result)
    
    @staticmethod
    def _generate_comparison_fallback(items: List[Dict[str, Any]], title: str) -> str:
        """Generate a text fallback for a comparison widget."""
        if not items:
            return "No comparison data available."
            
        lines = [title, '-' * len(title), '']
        
        for item in items:
            lines.append(f"{item['label']}: {item['value']}")
            
        return '\n'.join(lines)
    
    @staticmethod
    def _generate_options_fallback(options: List[Dict[str, Any]], question: str) -> str:
        """Generate a text fallback for an options widget."""
        if not options:
            return "No options available."
            
        lines = [question, '']
        
        for i, option in enumerate(options):
            desc = f" - {option.get('description')}" if option.get('description') else ""
            lines.append(f"{i+1}. {option['label']}{desc}")
            
        return '\n'.join(lines)


# Sample usage in answer_node:
"""
def answer_node(state: AgentState) -> AgentState:
    # ... existing code ...
    
    # Extract data from SQL result
    sql_result_obj = state['sql_result'][-1] if state.get('sql_result') and len(state['sql_result']) > 0 else {}
    data = sql_result_obj.get('data', [])
    success = sql_result_obj.get('success', False)
    
    if not success:
        # Handle error case
        error_message = sql_result_obj.get('error')
        return {
            **state,
            'final_answer': WidgetFormatter.format_response(
                f"Error: {error_message}", 
                widget_type="text"
            )
        }
    
    # Format the response using the widget formatter
    formatted_response = WidgetFormatter.format_response(
        data=data,
        query=state['query']
        # widget_type is auto-detected
    )
    
    return {
        **state,
        'final_answer': formatted_response
    }
"""