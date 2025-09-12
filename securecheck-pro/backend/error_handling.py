"""
Error handling utilities and custom exceptions
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityAnalysisError(Exception):
    """Base exception for security analysis errors"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class SSLAnalysisError(SecurityAnalysisError):
    """Exception for SSL analysis specific errors"""
    pass


class PDFGenerationError(SecurityAnalysisError):
    """Exception for PDF generation errors"""
    pass


class ConfigurationError(SecurityAnalysisError):
    """Exception for configuration errors"""
    pass


class ErrorHandler:
    """Central error handler for the application"""
    
    @staticmethod
    def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Log error with context information"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }
        
        if context:
            error_info['context'] = context
        
        logger.error(f"Application error occurred: {error_info}")
    
    @staticmethod
    def handle_analysis_error(error: Exception, analysis_id: str, url: str) -> HTTPException:
        """Handle analysis-related errors"""
        ErrorHandler.log_error(error, {'analysis_id': analysis_id, 'url': url})
        
        if isinstance(error, SSLAnalysisError):
            return HTTPException(
                status_code=422,
                detail=f"SSL 분석 중 오류가 발생했습니다: {str(error)}"
            )
        elif isinstance(error, ValueError):
            return HTTPException(
                status_code=400,
                detail=f"잘못된 요청 데이터입니다: {str(error)}"
            )
        else:
            return HTTPException(
                status_code=500,
                detail=f"분석 중 예기치 않은 오류가 발생했습니다: {str(error)}"
            )
    
    @staticmethod
    def handle_pdf_generation_error(error: Exception, report_id: str) -> Dict[str, Any]:
        """Handle PDF generation errors"""
        ErrorHandler.log_error(error, {'report_id': report_id, 'operation': 'pdf_generation'})
        
        if isinstance(error, PDFGenerationError):
            return {
                "success": False,
                "error": f"PDF 생성 중 오류가 발생했습니다: {str(error)}",
                "error_code": "PDF_GENERATION_FAILED"
            }
        else:
            return {
                "success": False,
                "error": f"예기치 않은 오류가 발생했습니다: {str(error)}",
                "error_code": "UNEXPECTED_ERROR"
            }
    
    @staticmethod
    def create_error_response(message: str, error_code: str = "GENERAL_ERROR") -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": error_code,
            "timestamp": str(logger.handlers[0].formatter.formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )))
        }
    
    @staticmethod
    def safe_execute(func, *args, **kwargs) -> tuple[bool, Any]:
        """Safely execute a function and return success status and result"""
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            ErrorHandler.log_error(e)
            return False, None


class ValidationError(SecurityAnalysisError):
    """Exception for validation errors"""
    pass


class URLValidator:
    """URL validation utilities"""
    
    @staticmethod
    def validate_url(url: str) -> None:
        """Validate URL format and accessibility"""
        if not url or not url.strip():
            raise ValidationError("URL이 비어있습니다")
        
        url = url.strip()
        
        if not url.startswith(('http://', 'https://')):
            raise ValidationError("URL은 http:// 또는 https://로 시작해야 합니다")
        
        # Remove protocol and check domain
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        
        if not domain or '.' not in domain:
            raise ValidationError("올바른 도메인 형식이 아닙니다")
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', '"', "'", '&', ';']
        if any(char in url for char in suspicious_chars):
            raise ValidationError("URL에 허용되지 않는 문자가 포함되어 있습니다")


def safe_dict_get(dictionary: Dict[str, Any], key: str, default: Any = None, expected_type: type = None) -> Any:
    """Safely get value from dictionary with type checking"""
    try:
        value = dictionary.get(key, default)
        if expected_type and value is not None and not isinstance(value, expected_type):
            logger.warning(f"Type mismatch for key '{key}': expected {expected_type}, got {type(value)}")
            return default
        return value
    except Exception as e:
        logger.error(f"Error getting key '{key}' from dictionary: {e}")
        return default