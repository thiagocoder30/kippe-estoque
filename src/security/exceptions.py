class DomainException(Exception):
    """Base exception for all domain-related errors."""
    pass

class ValidationException(DomainException):
    """Raised when input validation fails before hitting the domain."""
    pass

class AuthorizationException(DomainException):
    """Raised when an operation is forbidden for the current execution context."""
    pass

class NotFoundException(DomainException):
    """Raised when an aggregate cannot be found in the repository."""
    pass

class BusinessRuleViolation(DomainException):
    """Raised when a business invariant is violated."""
    pass
