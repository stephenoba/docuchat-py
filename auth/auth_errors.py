class AuthError(Exception):
    message: str
    

class UserNotFoundError(AuthError):
    def __init__(self):
        self.message = "User not found"


class UserAlreadyExistsError(AuthError):
    def __init__(self, message: str = "User already exists"):
        self.message = message


class InactiveUserError(AuthError):
    def __init__(self, message: str = "User is inactive"):
        self.message = message


class InvalidPasswordError(AuthError):
    def __init__(self, message: str = "Invalid password"):
        self.message = message

class InvalidTokenError(AuthError):
    def __init__(self, message: str = "Invalid token"):
        self.message = message