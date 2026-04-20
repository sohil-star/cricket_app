from django.contrib import admin
from django.urls import path
from core import views  # <-- Apni app ka naam check kar lena, agar 'core' nahi hai toh badal dena

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/matches/', views.get_all_matches, name='get_all_matches'),
    path('api/matches/<int:match_id>/', views.get_match_detail, name='get_match_detail'),
    path('api/update-score/<int:match_id>/', views.update_score, name='update_score'),
    path('api/change-player/<int:match_id>/', views.change_player, name='change_player'),
    
    # --- YEH NAYI LINE TOSS KE LIYE ZAROORI HAI ---
    path('api/toss/<int:match_id>/', views.update_toss, name='update_toss'),
    # --- YEH NAYI LINE UNDO KE LIYE HAI ---
    path('api/undo/<int:match_id>/', views.undo_ball, name='undo_ball'),
    path('api/leaderboard/', views.get_leaderboard, name='get_leaderboard'), 
]