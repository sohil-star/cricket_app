from django.shortcuts import render
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Match, BallHistory, Player, Team 

@api_view(['GET'])
def get_all_matches(request):
    matches = Match.objects.all()
    data = [{"id": m.id, "teams": f"{m.team_a_name} vs {m.team_b_name}"} for m in matches]
    return Response(data)

@api_view(['POST'])
def update_toss(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        match.toss_winner = request.data.get('winner')
        match.toss_decision = request.data.get('decision')
        match.save()
        return Response({"status": "Toss Updated"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
def get_match_detail(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        recent_objs = BallHistory.objects.filter(match=match).order_by('-timestamp')[:30]
        history = [b.ball_result for b in recent_objs][::-1] 

        # --- TOSS LOGIC FOR BATTING TEAM ---
        team_a = match.team_a
        team_b = match.team_b

        if match.toss_winner and match.toss_decision:
            if match.toss_decision == 'bat':
                bat_team = team_a if match.toss_winner == match.team_a_name else team_b
                bowl_team = team_b if match.toss_winner == match.team_a_name else team_a
            else: # Elected to bowl
                bowl_team = team_a if match.toss_winner == match.team_a_name else team_b
                bat_team = team_b if match.toss_winner == match.team_a_name else team_a
        else:
            bat_team = team_a
            bowl_team = team_b

        # Swap for 2nd innings
        if match.current_innings == 2:
            bat_team, bowl_team = bowl_team, bat_team
        
        batting_done = Player.objects.filter(team=bat_team, balls_faced__gt=0).values('name', 'runs_scored', 'balls_faced', 'fours', 'sixes')
        did_not_bat = Player.objects.filter(team=bat_team, balls_faced=0).exclude(name__in=[match.current_batsman, match.non_striker]).values('name')

        active_bowler_stats = Player.objects.filter(name__iexact=match.current_bowler).values('name', 'overs_bowled', 'runs_conceded', 'wickets_taken').first()
        bowling_done = Player.objects.filter(team=bowl_team, overs_bowled__gt=0).exclude(name__iexact=match.current_bowler).values('name', 'overs_bowled', 'runs_conceded', 'wickets_taken')
        did_not_bowl = Player.objects.filter(team=bowl_team, overs_bowled=0).exclude(name__iexact=match.current_bowler).values('name')

        data = {
            "id": match.id,
            "team_a_name": match.team_a_name, "team_b_name": match.team_b_name,
            "toss_winner": match.toss_winner, "toss_decision": match.toss_decision,
            "batting_team": bat_team.name if bat_team else "Team A",
            "bowling_team": bowl_team.name if bowl_team else "Team B",
            "total_runs": match.total_runs, "wickets": match.wickets,
            "overs": match.overs, "balls_in_over": match.balls_in_over,
            "total_overs": match.total_overs,
            "current_batsman": match.current_batsman, "non_striker": match.non_striker,
            "current_bowler": match.current_bowler,
            "striker_runs": match.striker_runs, "striker_balls": match.striker_balls,
            "non_striker_runs": match.non_striker_runs, "non_striker_balls": match.non_striker_balls,
            "recent_balls": history,
            "current_innings": match.current_innings,
            "target_score": match.target_score,
            "is_finished": match.is_finished,
            "match_result": match.match_result,
            "batting_card": list(batting_done),
            "did_not_bat": list(did_not_bat),
            "active_bowler": active_bowler_stats,
            "bowling_done": list(bowling_done),
            "did_not_bowl": list(did_not_bowl)
        }
        return Response(data)
    except Match.DoesNotExist:
        return Response({"error": "Match not found"}, status=404)
@api_view(['POST'])
def update_score(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        if match.is_finished: return Response({"error": "Match finished"}, status=400)

        runs = int(request.data.get('runs', 0))
        is_wicket = request.data.get('is_wicket', False)
        extra_type = request.data.get('extra_type', None)

        striker_obj = Player.objects.filter(name__iexact=match.current_batsman).first()
        bowler_obj = Player.objects.filter(name__iexact=match.current_bowler).first()
        ball_tag = str(runs)
        should_swap = False

        if match.balls_in_over == 0 and not extra_type:
            BallHistory.objects.create(match=match, ball_result=f"OV {match.overs + 1}")

        # Core Scoring Logic
        if is_wicket:
            match.wickets += 1
            ball_tag = "W"
            if striker_obj: striker_obj.balls_faced += 1
            if bowler_obj: 
                bowler_obj.wickets_taken += 1
                bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
            match.striker_runs = 0
            match.striker_balls = 0
        elif extra_type == 'wide':
            match.total_runs += (1 + runs)
            if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
            ball_tag = "wd" if runs == 0 else f"{runs}wd"
            if runs in [1, 3, 5]: should_swap = True
        elif extra_type == 'noball':
            match.total_runs += (1 + runs)
            match.striker_runs += runs
            if striker_obj: striker_obj.runs_scored += runs
            if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
            ball_tag = "nb" if runs == 0 else f"{runs}nb"
            if runs in [1, 3, 5]: should_swap = True
        elif extra_type == 'legbye':
            match.total_runs += runs
            match.balls_in_over += 1
            match.striker_balls += 1
            if striker_obj: striker_obj.balls_faced += 1
            if bowler_obj: bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
            ball_tag = f"{runs}lb"
            if runs in [1, 3, 5]: should_swap = True
        else:
            match.total_runs += runs
            match.balls_in_over += 1
            match.striker_runs += runs
            match.striker_balls += 1
            if striker_obj:
                striker_obj.runs_scored += runs
                striker_obj.balls_faced += 1
                if runs == 4: striker_obj.fours += 1
                if runs == 6: striker_obj.sixes += 1
            if bowler_obj:
                bowler_obj.runs_conceded += runs
                bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
            if runs in [1, 3, 5]: should_swap = True

        # NAYA OVER CALCULATION LOGIC
        current_ball_runs = runs
        if extra_type in ['wide', 'noball']: current_ball_runs += 1
        
        over_just_finished = False
        runs_in_over = 0

        if match.balls_in_over == 6:
            match.overs += 1
            match.balls_in_over = 0
            should_swap = not should_swap
            over_just_finished = True
            if bowler_obj: bowler_obj.overs_bowled = float(int(bowler_obj.overs_bowled) + 1)
            
            last_ov_marker = BallHistory.objects.filter(match=match, ball_result__startswith="OV").order_by('-timestamp').first()
            over_runs_so_far = 0
            if last_ov_marker:
                balls_this_over = BallHistory.objects.filter(match=match, timestamp__gt=last_ov_marker.timestamp)
                for b in balls_this_over:
                    tag = b.ball_result
                    if 'wd' in tag:
                        val = tag.replace('wd', '')
                        over_runs_so_far += (1 + int(val)) if val else 1
                    elif 'nb' in tag:
                        val = tag.replace('nb', '')
                        over_runs_so_far += (1 + int(val)) if val else 1
                    elif 'lb' in tag:
                        val = tag.replace('lb', '')
                        over_runs_so_far += int(val) if val else 0
                    elif tag == 'W' or 'TARGET' in tag or '=' in tag:
                        pass
                    elif tag.isdigit():
                        over_runs_so_far += int(tag)
            
            runs_in_over = over_runs_so_far + current_ball_runs

        if should_swap:
            match.current_batsman, match.non_striker = match.non_striker, match.current_batsman
            match.striker_runs, match.non_striker_runs = match.non_striker_runs, match.striker_runs
            match.striker_balls, match.non_striker_balls = match.non_striker_balls, match.striker_balls


        # --- 🏆 PERFECT TEAM NAME LOGIC ---
        team_a = match.team_a_name or "Team A"
        team_b = match.team_b_name or "Team B"

        if match.toss_winner and match.toss_decision:
            if match.toss_decision == 'bat':
                inn1_bat = match.toss_winner
                inn1_bowl = team_b if match.toss_winner == team_a else team_a
            else:
                inn1_bowl = match.toss_winner
                inn1_bat = team_b if match.toss_winner == team_a else team_a
        else:
            inn1_bat = team_a
            inn1_bowl = team_b
            
        current_batting_team = inn1_bowl if match.current_innings == 2 else inn1_bat
        current_bowling_team = inn1_bat if match.current_innings == 2 else inn1_bowl
        # ----------------------------------


        # 1st Inning Ends
        if match.current_innings == 1:
            if match.overs == match.total_overs or match.wickets >= 10:
                match.target_score = match.total_runs + 1
                match.current_innings = 2
                match.total_runs, match.wickets, match.overs, match.balls_in_over = 0, 0, 0, 0
                match.striker_runs, match.striker_balls = 0, 0
                match.non_striker_runs, match.non_striker_balls = 0, 0
                BallHistory.objects.create(match=match, ball_result=f"TARGET: {match.target_score}")
        
        # 2nd Inning Ends
        elif match.current_innings == 2:
            if match.total_runs >= match.target_score:
                match.is_finished = True
                match.match_result = f"🏆 {current_batting_team} won by {10 - match.wickets} wickets"
            elif match.overs == match.total_overs or match.wickets >= 10:
                match.is_finished = True
                if match.total_runs == match.target_score - 1:
                    match.match_result = "🤝 Match Tied!"
                else:
                    runs_short = (match.target_score - 1) - match.total_runs
                    match.match_result = f"🏆 {current_bowling_team} won by {runs_short} runs"

        match.save()
        if striker_obj: striker_obj.save()
        if bowler_obj: bowler_obj.save()
        
        BallHistory.objects.create(match=match, ball_result=ball_tag)
        if over_just_finished: 
            BallHistory.objects.create(match=match, ball_result=f"= {runs_in_over} Runs")

        return Response({"status": "Updated"})
    except Exception as e:
        return Response({"error": str(e)}, status=400) 
# @api_view(['POST'])
# def update_score(request, match_id):
#     try:
#         match = Match.objects.get(id=match_id)
#         if match.is_finished: return Response({"error": "Match finished"}, status=400)

#         runs = int(request.data.get('runs', 0))
#         is_wicket = request.data.get('is_wicket', False)
#         extra_type = request.data.get('extra_type', None)

#         striker_obj = Player.objects.filter(name__iexact=match.current_batsman).first()
#         bowler_obj = Player.objects.filter(name__iexact=match.current_bowler).first()
#         ball_tag = str(runs)
#         should_swap = False

#         if match.balls_in_over == 0 and not extra_type:
#             BallHistory.objects.create(match=match, ball_result=f"OV {match.overs + 1}")

#         # Core Scoring Logic
#         if is_wicket:
#             match.wickets += 1
#             ball_tag = "W"
#             if striker_obj: striker_obj.balls_faced += 1
#             if bowler_obj: 
#                 bowler_obj.wickets_taken += 1
#                 bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
#             match.striker_runs = 0
#             match.striker_balls = 0
#         elif extra_type == 'wide':
#             match.total_runs += (1 + runs)
#             if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
#             ball_tag = "wd" if runs == 0 else f"{runs}wd"
#             if runs in [1, 3, 5]: should_swap = True
#         elif extra_type == 'noball':
#             match.total_runs += (1 + runs)
#             match.striker_runs += runs
#             if striker_obj: striker_obj.runs_scored += runs
#             if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
#             ball_tag = "nb" if runs == 0 else f"{runs}nb"
#             if runs in [1, 3, 5]: should_swap = True
#         elif extra_type == 'legbye':
#             match.total_runs += runs
#             match.balls_in_over += 1
#             match.striker_balls += 1
#             if striker_obj: striker_obj.balls_faced += 1
#             if bowler_obj: bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
#             ball_tag = f"{runs}lb"
#             if runs in [1, 3, 5]: should_swap = True
#         else:
#             match.total_runs += runs
#             match.balls_in_over += 1
#             match.striker_runs += runs
#             match.striker_balls += 1
#             if striker_obj:
#                 striker_obj.runs_scored += runs
#                 striker_obj.balls_faced += 1
#             if bowler_obj:
#                 bowler_obj.runs_conceded += runs
#                 bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
#             if runs in [1, 3, 5]: should_swap = True

#         # --- NAYA OVER CALCULATION LOGIC ---
#         current_ball_runs = runs
#         if extra_type in ['wide', 'noball']: current_ball_runs += 1
        
#         over_just_finished = False
#         runs_in_over = 0

#         if match.balls_in_over == 6:
#             match.overs += 1
#             match.balls_in_over = 0
#             should_swap = not should_swap
#             over_just_finished = True
#             if bowler_obj: bowler_obj.overs_bowled = float(int(bowler_obj.overs_bowled) + 1)
            
#             # Yahan hum BallHistory se check kar rahe hain us over mein kitne runs bane
#             last_ov_marker = BallHistory.objects.filter(match=match, ball_result__startswith="OV").order_by('-timestamp').first()
#             over_runs_so_far = 0
#             if last_ov_marker:
#                 balls_this_over = BallHistory.objects.filter(match=match, timestamp__gt=last_ov_marker.timestamp)
#                 for b in balls_this_over:
#                     tag = b.ball_result
#                     if 'wd' in tag:
#                         val = tag.replace('wd', '')
#                         over_runs_so_far += (1 + int(val)) if val else 1
#                     elif 'nb' in tag:
#                         val = tag.replace('nb', '')
#                         over_runs_so_far += (1 + int(val)) if val else 1
#                     elif 'lb' in tag:
#                         val = tag.replace('lb', '')
#                         over_runs_so_far += int(val) if val else 0
#                     elif tag == 'W' or 'TARGET' in tag or '=' in tag:
#                         pass
#                     elif tag.isdigit():
#                         over_runs_so_far += int(tag)
            
#             runs_in_over = over_runs_so_far + current_ball_runs

#         if should_swap:
#             match.current_batsman, match.non_striker = match.non_striker, match.current_batsman
#             match.striker_runs, match.non_striker_runs = match.non_striker_runs, match.striker_runs
#             match.striker_balls, match.non_striker_balls = match.non_striker_balls, match.striker_balls

#         # 1st Inning Ends
#         if match.current_innings == 1:
#             if match.overs == match.total_overs or match.wickets >= 10:
#                 match.target_score = match.total_runs + 1
#                 match.current_innings = 2
#                 match.total_runs, match.wickets, match.overs, match.balls_in_over = 0, 0, 0, 0
#                 match.striker_runs, match.striker_balls = 0, 0
#                 match.non_striker_runs, match.non_striker_balls = 0, 0
#                 BallHistory.objects.create(match=match, ball_result=f"TARGET: {match.target_score}")
        
#         # 2nd Inning Ends
#         # 2nd Inning Ends
#         elif match.current_innings == 2:
#             if match.total_runs >= match.target_score:
#                 match.is_finished = True
#                 # FIX: Hum direct striker ki team ka naam use kar lenge
#                 winning_team = striker_obj.team.name if striker_obj else "Batting Team"
#                 match.match_result = f"{winning_team} won the match!"
                
#             elif match.overs == match.total_overs or match.wickets >= 10:
#                 match.is_finished = True
#                 if match.total_runs == match.target_score - 1:
#                     match.match_result = "Match Tied!"
#                 else:
#                     # Agar target pura nahi hua toh dusri team jeetegi
#                     winning_team = bowler_obj.team.name if bowler_obj else "Bowling Team"
#                     match.match_result = f"{winning_team} won the match!"
#         # elif match.current_innings == 2:
#         #     if match.total_runs >= match.target_score:
#         #         match.is_finished = True
#         #         match.match_result = f"{match.batting_team} won"
#         #     elif match.overs == match.total_overs or match.wickets >= 10:
#         #         match.is_finished = True
#         #         match.match_result = "Match Finished"

#         match.save()
#         if striker_obj: striker_obj.save()
#         if bowler_obj: bowler_obj.save()
        
#         # Current Ball record
#         BallHistory.objects.create(match=match, ball_result=ball_tag)
        
#         # Over Total Timeline Update
#         if over_just_finished: 
#             BallHistory.objects.create(match=match, ball_result=f"= {runs_in_over} Runs")

#         return Response({"status": "Updated"})
#     except Exception as e:
#         return Response({"error": str(e)}, status=400)
# @api_view(['POST'])
# def update_score(request, match_id):
#     try:
#         match = Match.objects.get(id=match_id)
#         if match.is_finished: return Response({"error": "Match finished"}, status=400)

#         runs = int(request.data.get('runs', 0))
#         is_wicket = request.data.get('is_wicket', False)
#         extra_type = request.data.get('extra_type', None)

#         striker_obj = Player.objects.filter(name__iexact=match.current_batsman).first()
#         bowler_obj = Player.objects.filter(name__iexact=match.current_bowler).first()
#         ball_tag = str(runs)
#         should_swap = False

#         if match.balls_in_over == 0 and not extra_type:
#             match.last_total_marker = match.total_runs 
#             BallHistory.objects.create(match=match, ball_result=f"OV {match.overs + 1}")

#         if is_wicket:
#             match.wickets += 1
#             ball_tag = "W"
#             if striker_obj: striker_obj.balls_faced += 1
#             if bowler_obj: 
#                 bowler_obj.wickets_taken += 1
#                 bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
#             match.striker_runs = 0
#             match.striker_balls = 0
#         elif extra_type == 'wide':
#             match.total_runs += (1 + runs)
#             if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
#             ball_tag = "wd" if runs == 0 else f"{runs}wd"
#             if runs in [1, 3, 5]: should_swap = True
#         elif extra_type == 'noball':
#             match.total_runs += (1 + runs)
#             match.striker_runs += runs
#             if striker_obj: striker_obj.runs_scored += runs
#             if bowler_obj: bowler_obj.runs_conceded += (1 + runs)
#             ball_tag = "nb" if runs == 0 else f"{runs}nb"
#             if runs in [1, 3, 5]: should_swap = True
#         else:
#             match.total_runs += runs
#             match.balls_in_over += 1
#             match.striker_runs += runs
#             match.striker_balls += 1
#             if striker_obj:
#                 striker_obj.runs_scored += runs
#                 striker_obj.balls_faced += 1
#             if bowler_obj:
#                 bowler_obj.runs_conceded += runs
#                 bowler_obj.overs_bowled = round(float(bowler_obj.overs_bowled) + 0.1, 1)
#             if runs in [1, 3, 5]: should_swap = True

#         over_just_finished = False
#         if match.balls_in_over == 6:
#             match.overs += 1
#             match.balls_in_over = 0
#             should_swap = not should_swap
#             over_just_finished = True
#             runs_in_over = match.total_runs - getattr(match, 'last_total_marker', 0)
#             if bowler_obj: bowler_obj.overs_bowled = float(int(bowler_obj.overs_bowled) + 1)

#         if should_swap:
#             match.current_batsman, match.non_striker = match.non_striker, match.current_batsman
#             match.striker_runs, match.non_striker_runs = match.non_striker_runs, match.striker_runs
#             match.striker_balls, match.non_striker_balls = match.non_striker_balls, match.striker_balls

#         if match.current_innings == 1:
#             if match.overs == match.total_overs or match.wickets >= 10:
#                 match.target_score = match.total_runs + 1
#                 match.current_innings = 2
#                 match.total_runs, match.wickets, match.overs, match.balls_in_over = 0, 0, 0, 0
#                 match.striker_runs, match.striker_balls = 0, 0
#                 match.non_striker_runs, match.non_striker_balls = 0, 0
#                 BallHistory.objects.create(match=match, ball_result=f"TARGET: {match.target_score}")
        
#         elif match.current_innings == 2:
#             if match.total_runs >= match.target_score:
#                 match.is_finished = True
#                 match.match_result = f"{match.batting_team} won"
#             elif match.overs == match.total_overs or match.wickets >= 10:
#                 match.is_finished = True
#                 match.match_result = "Match Finished"

#         match.save()
#         if striker_obj: striker_obj.save()
#         if bowler_obj: bowler_obj.save()
        
#         BallHistory.objects.create(match=match, ball_result=ball_tag)
#         if over_just_finished: BallHistory.objects.create(match=match, ball_result=f"= {runs_in_over} Runs")

#         return Response({"status": "Updated"})
#     except Exception as e:
#         return Response({"error": str(e)}, status=400)

@api_view(['POST'])
def change_player(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        role = request.data.get('role') 
        new_name = request.data.get('name')
        if role == 'striker': match.current_batsman = new_name
        elif role == 'non_striker': match.non_striker = new_name
        elif role == 'bowler': match.current_bowler = new_name
        match.save()
        return Response({'status': 'Player Updated'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def undo_ball(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        # Pichli 5 history fetch karte hain taaki marker (OV, =, TARGET) skip kar sakein
        history_items = list(BallHistory.objects.filter(match=match).order_by('-timestamp')[:5])
        
        items_to_delete = []
        action_ball = None
        
        for item in history_items:
            items_to_delete.append(item)
            # Find the actual playable ball (Ignore markers)
            if not (item.ball_result.startswith('=') or item.ball_result.startswith('OV') or item.ball_result.startswith('TARGET')):
                action_ball = item
                break
                
        if not action_ball:
            return Response({"error": "Undo ke liye koi pichli ball nahi mili"}, status=400)
            
        tag = action_ball.ball_result
        striker = Player.objects.filter(name__iexact=match.current_batsman).first()
        bowler = Player.objects.filter(name__iexact=match.current_bowler).first()
        
        did_swap = False
        
        # --- REVERSE LOGIC ---
        if 'wd' in tag:
            runs = int(tag.replace('wd', '')) if tag != 'wd' else 0
            match.total_runs -= (runs + 1)
            if bowler: bowler.runs_conceded -= (runs + 1)
            if runs in [1, 3, 5]: did_swap = True
            
        elif 'nb' in tag:
            runs = int(tag.replace('nb', '')) if tag != 'nb' else 0
            match.total_runs -= (runs + 1)
            match.striker_runs -= runs
            if striker: 
                striker.runs_scored -= runs
                if runs == 4: striker.fours -= 1
                if runs == 6: striker.sixes -= 1
            if bowler: bowler.runs_conceded -= (runs + 1)
            if runs in [1, 3, 5]: did_swap = True
            
        elif 'lb' in tag:
            runs = int(tag.replace('lb', ''))
            match.total_runs -= runs
            match.striker_balls -= 1
            if match.balls_in_over == 0: match.overs -= 1; match.balls_in_over = 5
            else: match.balls_in_over -= 1
            if striker: striker.balls_faced -= 1
            if runs in [1, 3, 5]: did_swap = True
            
        elif tag == 'W':
            match.wickets -= 1
            match.striker_balls -= 1
            if match.balls_in_over == 0: match.overs -= 1; match.balls_in_over = 5
            else: match.balls_in_over -= 1
            if striker: striker.balls_faced -= 1
            if bowler: bowler.wickets_taken -= 1
            
        else:
            runs = int(tag)
            match.total_runs -= runs
            match.striker_runs -= runs
            match.striker_balls -= 1
            if match.balls_in_over == 0: match.overs -= 1; match.balls_in_over = 5
            else: match.balls_in_over -= 1
            
            if striker:
                striker.runs_scored -= runs
                striker.balls_faced -= 1
                if runs == 4: striker.fours -= 1
                if runs == 6: striker.sixes -= 1
            if bowler: bowler.runs_conceded -= runs
            if runs in [1, 3, 5]: did_swap = True

        # Handle Bowler Overs Wrap (e.g., Undo 1.0 -> 0.5)
        if tag not in ['wd', 'nb'] and bowler:
            if match.balls_in_over == 5:
                current_over = int(bowler.overs_bowled)
                if current_over > 0: bowler.overs_bowled = float(current_over - 1) + 0.5
            else:
                bowler.overs_bowled = round(float(bowler.overs_bowled) - 0.1, 1)

        # Reverse Strike Rotation
        if did_swap:
            match.current_batsman, match.non_striker = match.non_striker, match.current_batsman
            match.striker_runs, match.non_striker_runs = match.non_striker_runs, match.striker_runs
            match.striker_balls, match.non_striker_balls = match.non_striker_balls, match.striker_balls

        # Delete from Timeline
        for item in items_to_delete:
            item.delete()
            
        match.is_finished = False
        match.match_result = ""
        match.save()
        if striker: striker.save()
        if bowler: bowler.save()
        
        return Response({"status": "Undo Successful"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)    
@api_view(['GET'])
def get_leaderboard(request):
    try:
        # 1. Top 5 Batsmen (Orange Cap)
        top_batsmen = Player.objects.order_by('-runs_scored')[:5].values('name', 'team__name', 'runs_scored', 'balls_faced', 'sixes', 'fours')
        
        # 2. Top 5 Bowlers (Purple Cap)
        top_bowlers = Player.objects.order_by('-wickets_taken', 'runs_conceded')[:5].values('name', 'team__name', 'wickets_taken', 'overs_bowled', 'runs_conceded')
        
        # 3. Points Table Calculation
        teams = Team.objects.all()
        points_table = []
        for team in teams:
            played = Match.objects.filter(is_finished=True).filter(Q(team_a=team) | Q(team_b=team)).count()
            won = Match.objects.filter(is_finished=True, match_result__icontains=team.name).count()
            tied = Match.objects.filter(is_finished=True, match_result__icontains="Tied").filter(Q(team_a=team) | Q(team_b=team)).count()
            lost = played - won - tied
            points = (won * 2) + (tied * 1)
            
            points_table.append({
                "team": team.name,
                "played": played, "won": won, "lost": lost, "tied": tied, "points": points
            })
        
        # Points ke hisaab se sort karna (Highest points upar)
        points_table = sorted(points_table, key=lambda x: x['points'], reverse=True)

        return Response({
            "top_batsmen": list(top_batsmen),
            "top_bowlers": list(top_bowlers),
            "points_table": points_table
        })
    except Exception as e:
        return Response({"error": str(e)}, status=400)    