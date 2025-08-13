def is_admin(user):
    if user.is_superuser:
        return True
    if hasattr(user, 'personnel_profile'):
        return user.personnel_profile.is_admin
    return False