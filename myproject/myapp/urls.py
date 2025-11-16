from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('', views.home_view, name='home'),
    path('available-pigs/', views.available_pigs_view, name='available_pigs'),
    path('reservation/', views.reservation_view, name='reservation'),
    path('reservation/<int:pig_id>/', views.reservation_view, name='reservation_with_pig'),
    path('description/', views.description_view, name='description'),
    path('logout-confirm/', views.logout_confirm_view, name='logout_confirm'),
    
    # User Profile Management
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Customer Reservation Management
    path('my-reservations/', views.customer_reservation_list, name='customer_reservation_list'),
    path('my-reservations/edit/<int:reservation_id>/', views.customer_reservation_edit, name='customer_reservation_edit'),
    path('my-reservations/delete/<int:reservation_id>/', views.customer_reservation_delete, name='customer_reservation_delete'),
    path('purchase-now/<int:pig_id>/', views.purchase_now, name='purchase_now'),
    
    # Customer Feedback
    path('feedback/<int:reservation_id>/', views.feedback_form, name='feedback_form'),
    
    # Cart Management
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:pig_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/checkout/', views.checkout_cart, name='checkout_cart'),
    
    # Admin Pig Management
    path('manage/pigs/add/', views.admin_pig_add, name='admin_pig_add'),
    path('manage/pigs/edit/<int:pig_id>/', views.admin_pig_edit, name='admin_pig_edit'),
    path('manage/pigs/delete/<int:pig_id>/', views.admin_pig_delete, name='admin_pig_delete'),
    
    # Admin User Management
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    path('manage/users/add/', views.admin_user_add, name='admin_user_add'),
    path('manage/users/edit/<int:user_id>/', views.admin_user_edit, name='admin_user_edit'),
    path('manage/users/change-password/<int:user_id>/', views.admin_user_change_password, name='admin_user_change_password'),
    path('manage/users/delete/<int:user_id>/', views.admin_user_delete, name='admin_user_delete'),
    
    # Admin Reservation Management
    path('manage/reservations/', views.admin_reservation_list, name='admin_reservation_list'),
    path('manage/reservations/create/', views.admin_create_reservation, name='admin_create_reservation'),
    path('manage/reservations/view/<int:reservation_id>/', views.admin_reservation_view, name='admin_reservation_view'),
    path('manage/reservations/edit/<int:reservation_id>/', views.admin_reservation_edit, name='admin_reservation_edit'),
    path('manage/reservations/delete/<int:reservation_id>/', views.admin_reservation_delete, name='admin_reservation_delete'),
    path('manage/reservations/confirm/<int:reservation_id>/', views.admin_reservation_confirm, name='admin_reservation_confirm'),
    path('manage/reservations/complete/<int:reservation_id>/', views.admin_reservation_complete, name='admin_reservation_complete'),
    path('manage/reservations/mark-complete/<int:reservation_id>/', views.complete_order, name='complete_order'),
    path('manage/reservations/update-status/<int:reservation_id>/', views.admin_reservation_update_status, name='admin_reservation_update_status'),
    
    # Admin Feedback Management
    path('manage/feedback/', views.admin_feedback_list, name='admin_feedback_list'),
    path('admin/feedback/<int:feedback_id>/', views.admin_feedback_detail, name='admin_feedback_detail'),
    
    # Revenue Management
    path('manage/revenue/', views.revenue_dashboard, name='revenue_dashboard'),
    
    # Tracking Records
    path('manage/tracking-records/', views.tracking_records, name='tracking_records'),
    
    # Messaging System
    path('send-message/', views.send_message, name='send_message'),
    path('my-messages/', views.my_messages, name='my_messages'),
    path('conversation/<int:conversation_id>/', views.customer_conversation, name='customer_conversation'),
    path('send-reply/<int:message_id>/', views.send_reply, name='send_reply'),
    path('delete-conversation/<int:message_id>/', views.delete_conversation, name='delete_conversation'),
    path('manage/inbox/', views.admin_inbox, name='admin_inbox'),
    path('manage/conversation/<int:conversation_id>/', views.admin_conversation, name='admin_conversation'),
    path('manage/conversation/<int:conversation_id>/delete/', views.admin_conversation_delete, name='admin_conversation_delete'),
    
    # API endpoints
    path('api/pending-orders-count/', views.pending_count_api, name='pending_count_api'),
    path('api/pending-orders/', views.pending_orders_api, name='pending_orders_api'),
    path('api/decline-notifications/', views.decline_notifications_api, name='decline_notifications_api'),
    path('api/toggle-payment-status/<int:reservation_id>/', views.toggle_payment_status, name='toggle_payment_status'),
    path('api/admin-status/', views.admin_status_api, name='admin_status_api'),
    path('api/user-status/<int:user_id>/', views.user_status_api, name='user_status_api'),
    path('api/check-accepted-orders/', views.check_accepted_orders_api, name='check_accepted_orders_api'),
    path('api/get-payment-details/', views.get_payment_details_api, name='get_payment_details_api'),
    path('api/upload-payment-proof/<int:reservation_id>/', views.upload_payment_proof_api, name='upload_payment_proof_api'),
    path('api/check-message-status/<int:conversation_id>/', views.check_message_status_api, name='check_message_status_api'),
]
