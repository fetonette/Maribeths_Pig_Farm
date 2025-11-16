from .models import Cart

def cart_count(request):
    """Add cart count to all templates"""
    if request.user.is_authenticated:
        count = Cart.objects.filter(user=request.user).count()
        return {'cart_count': count}
    return {'cart_count': 0}
