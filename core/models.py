from django.db import models

class Tournament(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Team(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    runs_scored = models.IntegerField(default=0)
    balls_faced = models.IntegerField(default=0)
    fours = models.IntegerField(default=0)
    sixes = models.IntegerField(default=0)
    singles = models.IntegerField(default=0)
    overs_bowled = models.FloatField(default=0.0)
    runs_conceded = models.IntegerField(default=0)
    wickets_taken = models.IntegerField(default=0)
    def __str__(self): return f"{self.name} ({self.team.name})"

class Match(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)
    team_a = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='match_team_a', null=True)
    team_b = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='match_team_b', null=True)
    team_a_name = models.CharField(max_length=100, null=True, blank=True)
    team_b_name = models.CharField(max_length=100, null=True, blank=True)
    
    # --- TOSS FEATURE ADDED ---
    toss_winner = models.CharField(max_length=100, null=True, blank=True)
    toss_decision = models.CharField(max_length=10, null=True, blank=True) # 'bat' or 'bowl'

    total_overs = models.IntegerField(default=10)
    total_runs = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0)
    overs = models.IntegerField(default=0)
    balls_in_over = models.IntegerField(default=0)
    current_innings = models.IntegerField(default=1)
    target_score = models.IntegerField(default=0)   
    is_finished = models.BooleanField(default=False)
    match_result = models.CharField(max_length=200, null=True, blank=True)
    last_total_marker = models.IntegerField(default=0) # Over runs fix

    current_batsman = models.CharField(max_length=100, default="Batsman 1")
    non_striker = models.CharField(max_length=100, default="Batsman 2")
    current_bowler = models.CharField(max_length=100, default="Bowler")
    striker_runs = models.IntegerField(default=0)
    striker_balls = models.IntegerField(default=0)
    non_striker_runs = models.IntegerField(default=0)
    non_striker_balls = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.team_a: self.team_a_name = self.team_a.name
        if self.team_b: self.team_b_name = self.team_b.name
        super().save(*args, **kwargs)

    def __str__(self):
        status = " (Finished)" if self.is_finished else " (Live)"
        return f"{self.team_a_name} vs {self.team_b_name}{status}"

class BallHistory(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='history')
    ball_result = models.CharField(max_length=20) 
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-timestamp']