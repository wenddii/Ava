def is_staff_user(user):
    """
    Check predicate ensuring the user is authenticated and has staff status.
    """
    return user.is_authenticated and user.is_staff
