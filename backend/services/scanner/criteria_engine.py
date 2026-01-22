import re
from typing import Dict, List, Any, Callable
from dataclasses import dataclass
import pandas as pd


@dataclass
class CriteriaNode:
    """Node in the criteria expression tree"""
    type: str  # 'operator', 'function', 'constant', 'variable'
    value: Any
    children: List['CriteriaNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class CriteriaParser:
    """
    Parser for Chartink-style criteria expressions
    
    Example expressions:
    - "RSI(14) > 70"
    - "Close > SMA(20) and Volume > SMA(Volume, 10) * 2"
    - "MACD() > MACD_Signal() and RSI(14) < 30"
    """
    
    # Supported operators
    OPERATORS = {
        'and': {'precedence': 1, 'function': lambda a, b: a & b},
        'or': {'precedence': 1, 'function': lambda a, b: a | b},
        '>': {'precedence': 2, 'function': lambda a, b: a > b},
        '<': {'precedence': 2, 'function': lambda a, b: a < b},
        '>=': {'precedence': 2, 'function': lambda a, b: a >= b},
        '<=': {'precedence': 2, 'function': lambda a, b: a <= b},
        '==': {'precedence': 2, 'function': lambda a, b: a == b},
        '!=': {'precedence': 2, 'function': lambda a, b: a != b},
        '+': {'precedence': 3, 'function': lambda a, b: a + b},
        '-': {'precedence': 3, 'function': lambda a, b: a - b},
        '*': {'precedence': 4, 'function': lambda a, b: a * b},
        '/': {'precedence': 4, 'function': lambda a, b: a / b},
    }
    
    # Supported variables (stock data fields)
    VARIABLES = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    def __init__(self):
        self.tokens = []
        self.position = 0
    
    def tokenize(self, expression: str) -> List[str]:
        """Tokenize the expression into components"""
        # Replace common variations
        expression = expression.replace(' and ', ' AND ')
        expression = expression.replace(' or ', ' OR ')
        
        # Regex pattern to match tokens
        pattern = r'(\w+\([^)]*\)|\w+|[<>=!]+|[+\-*/()]|AND|OR)'
        tokens = re.findall(pattern, expression)
        
        return [t.strip() for t in tokens if t.strip()]
    
    def parse(self, expression: str) -> CriteriaNode:
        """Parse expression into AST"""
        self.tokens = self.tokenize(expression)
        self.position = 0
        return self.parse_expression()
    
    def parse_expression(self, min_precedence: int = 0) -> CriteriaNode:
        """Parse expression using precedence climbing"""
        left = self.parse_primary()
        
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            
            if token.upper() in ['AND', 'OR']:
                token = token.lower()
            
            if token not in self.OPERATORS:
                break
            
            precedence = self.OPERATORS[token]['precedence']
            if precedence < min_precedence:
                break
            
            self.position += 1
            right = self.parse_expression(precedence + 1)
            
            left = CriteriaNode(
                type='operator',
                value=token,
                children=[left, right]
            )
        
        return left
    
    def parse_primary(self) -> CriteriaNode:
        """Parse primary expression (number, variable, function, or parenthesized expression)"""
        if self.position >= len(self.tokens):
            raise ValueError("Unexpected end of expression")
        
        token = self.tokens[self.position]
        
        # Parenthesized expression
        if token == '(':
            self.position += 1
            node = self.parse_expression()
            if self.position >= len(self.tokens) or self.tokens[self.position] != ')':
                raise ValueError("Missing closing parenthesis")
            self.position += 1
            return node
        
        # Function call (e.g., RSI(14), SMA(Close, 20))
        if '(' in token:
            return self.parse_function(token)
        
        # Number
        try:
            value = float(token)
            self.position += 1
            return CriteriaNode(type='constant', value=value)
        except ValueError:
            pass
        
        # Variable (Open, High, Low, Close, Volume)
        if token in self.VARIABLES:
            self.position += 1
            return CriteriaNode(type='variable', value=token)
        
        raise ValueError(f"Unexpected token: {token}")
    
    def parse_function(self, token: str) -> CriteriaNode:
        """Parse function call"""
        match = re.match(r'(\w+)\(([^)]*)\)', token)
        if not match:
            raise ValueError(f"Invalid function syntax: {token}")
        
        func_name = match.group(1)
        args_str = match.group(2)
        
        # Parse arguments
        args = []
        if args_str:
            arg_tokens = [arg.strip() for arg in args_str.split(',')]
            for arg in arg_tokens:
                # Check if arg is a number
                try:
                    args.append(CriteriaNode(type='constant', value=float(arg)))
                except ValueError:
                    # It's a variable
                    args.append(CriteriaNode(type='variable', value=arg))
        
        self.position += 1
        return CriteriaNode(
            type='function',
            value=func_name,
            children=args
        )


class CriteriaEvaluator:
    """Evaluate parsed criteria against stock data"""
    
    def __init__(self, indicators):
        self.indicators = indicators
        self.function_map = self._build_function_map()
    
    def _build_function_map(self) -> Dict[str, Callable]:
        """Map function names to indicator methods"""
        return {
            'SMA': self.indicators.sma,
            'EMA': self.indicators.ema,
            'RSI': self.indicators.rsi,
            'MACD': lambda data, *args: self.indicators.macd(data, *args)[0],
            'MACD_Signal': lambda data, *args: self.indicators.macd(data, *args)[1],
            'MACD_Hist': lambda data, *args: self.indicators.macd(data, *args)[2],
            'BB_Upper': lambda data, *args: self.indicators.bollinger_bands(data, *args)[0],
            'BB_Middle': lambda data, *args: self.indicators.bollinger_bands(data, *args)[1],
            'BB_Lower': lambda data, *args: self.indicators.bollinger_bands(data, *args)[2],
            'ATR': self.indicators.atr,
            'ADX': self.indicators.adx,
            'CCI': self.indicators.cci,
            'OBV': self.indicators.obv,
            'MFI': self.indicators.mfi,
            'VWAP': self.indicators.vwap,
            'Williams_R': self.indicators.williams_r,
        }
    
    def evaluate(self, node: CriteriaNode, data: pd.DataFrame) -> pd.Series:
        """Recursively evaluate criteria node"""
        if node.type == 'constant':
            # Return a series filled with the constant value
            return pd.Series([node.value] * len(data), index=data.index)
        
        elif node.type == 'variable':
            # Return the column from data
            return data[node.value]
        
        elif node.type == 'function':
            # Call the indicator function
            func_name = node.value
            if func_name not in self.function_map:
                raise ValueError(f"Unknown function: {func_name}")
            
            func = self.function_map[func_name]
            
            # Evaluate arguments
            args = []
            for child in node.children:
                if child.type == 'constant':
                    args.append(child.value)
                elif child.type == 'variable':
                    args.append(data[child.value])
                else:
                    args.append(self.evaluate(child, data))
            
            # Special handling for functions that need High, Low, Close
            if func_name in ['ATR', 'ADX', 'CCI', 'MFI']:
                result = func(data['High'], data['Low'], data['Close'], *args)
            elif func_name == 'OBV':
                result = func(data['Close'], data['Volume'])
            elif func_name == 'VWAP':
                result = func(data['High'], data['Low'], data['Close'], data['Volume'])
            else:
                # Most functions operate on Close by default
                if not args or isinstance(args[0], (int, float)):
                    result = func(data['Close'], *args)
                else:
                    result = func(*args)
            
            # Convert to Series if numpy array
            if isinstance(result, np.ndarray):
                result = pd.Series(result, index=data.index)
            
            return result
        
        elif node.type == 'operator':
            # Evaluate left and right children
            left = self.evaluate(node.children[0], data)
            right = self.evaluate(node.children[1], data)
            
            # Apply operator
            op_func = CriteriaParser.OPERATORS[node.value]['function']
            return op_func(left, right)
        
        else:
            raise ValueError(f"Unknown node type: {node.type}")
