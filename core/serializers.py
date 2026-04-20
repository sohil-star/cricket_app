from rest_framework import serializers
from .models import Tournament, Team, Player, Match

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = '__all__'

class TeamSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, read_only=True) # Team ke saath players bhi dikhenge
    class Meta:
        model = Team
        fields = '__all__'

class MatchSerializer(serializers.ModelSerializer):
    team_a_name = serializers.ReadOnlyField(source='team_a.name')
    team_b_name = serializers.ReadOnlyField(source='team_b.name')
    class Meta:
        model = Match
        fields = '__all__'
        