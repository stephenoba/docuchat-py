class AuthError(Exception):
    message: str
    

class UserNotFoundError(AuthError):
    def __init__(self):
        self.message = "User not found"


class UserAlreadyExistsError(AuthError):
    def __init__(self):
        self.message = "User already exists"


class InactiveUserError(AuthError):
    def __init__(self):
        self.message = "User is inactive"


class InvalidPasswordError(AuthError):
    def __init__(self):
        self.message = "Invalid password"