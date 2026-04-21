import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function App() {
  const [activeTab, setActiveTab] = useState('matches');
  const [matchList, setMatchList] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState(null); 
  const [match, setMatch] = useState(null);
  const [newPlayerName, setNewPlayerName] = useState("");
  const [pendingRuns, setPendingRuns] = useState(0); 
  const [errorMessage, setErrorMessage] = useState("Loading Matches..."); 
  
  const [tossWinner, setTossWinner] = useState("");
  const [tossDecision, setTossDecision] = useState("");
  const [leaderboard, setLeaderboard] = useState({ top_batsmen: [], top_bowlers: [], points_table: [] });

  const scrollRef = useRef(null);
  
  const BASE_URL = "https://sohilchauhan.pythonanywhere.com"; 
  const isViewer = window.location.search.includes('view=user');

  useEffect(() => {
    if (activeTab === 'matches') {
      axios.get(`${BASE_URL}/api/matches/`)
        .then(res => {
          if (Array.isArray(res.data)) {
            setMatchList(res.data);
            if (res.data.length === 0) setErrorMessage("Database mein koi match nahi hai.");
            else setErrorMessage("");
          }
        }).catch(err => setErrorMessage(`Backend se connection fail: ${err.message}`));
    } else if (activeTab === 'stats') {
      axios.get(`${BASE_URL}/api/leaderboard/`)
        .then(res => setLeaderboard(res.data))
        .catch(err => console.error("Leaderboard fetch error", err));
    }
  }, [activeTab]);

  const fetchScore = () => {
    if (!selectedMatchId || activeTab !== 'matches') return;
    axios.get(`${BASE_URL}/api/matches/${selectedMatchId}/`)
      .then(res => setMatch(res.data))
      .catch(err => console.log("Score error", err));
  };

  useEffect(() => {
    fetchScore();
    const interval = setInterval(fetchScore, 3000);
    return () => clearInterval(interval);
  }, [selectedMatchId, activeTab]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
  }, [match?.recent_balls]);

  const handleUpdate = (runs, isWicket = false, extraType = null) => {
    if (match?.is_finished) return; 
    
    if (extraType === 'legbye' && runs === 0) {
      alert("Bhai, Leg Bye ke liye pehle runs select karo phir LB button dabao!");
      return;
    }

    // Explicitly defining the payload to ensure backend catches everything properly
    const payload = {
      runs: runs ? parseInt(runs) : 0,
      is_wicket: isWicket,
      extra_type: extraType
    };

    axios.post(`${BASE_URL}/api/update-score/${selectedMatchId}/`, payload)
      .then(() => { 
        fetchScore(); 
        setPendingRuns(0); 
      })
      .catch(err => alert("Update fail: " + err.response?.data?.error));
  };

  const handleUndo = () => {
    if (window.confirm("⚠️ Are you sure? Pichli ball delete karni hai?")) {
      axios.post(`${BASE_URL}/api/undo/${selectedMatchId}/`)
        .then(() => fetchScore())
        .catch(err => alert("Undo fail ho gaya: " + err.response?.data?.error));
    }
  };

  const handleChangePlayer = (role) => {
    if(!newPlayerName) { alert("Pehle naam likho!"); return; }
    axios.post(`${BASE_URL}/api/change-player/${selectedMatchId}/`, { role, name: newPlayerName })
    .then(() => { setNewPlayerName(""); fetchScore(); })
    .catch(err => alert("Backend error!"));
  };

  const handleTossSubmit = () => {
    if (!tossWinner || !tossDecision) { alert("Bhai, winner aur decision dono select karo!"); return; }
    axios.post(`${BASE_URL}/api/toss/${selectedMatchId}/`, { winner: tossWinner, decision: tossDecision })
    .then(() => fetchScore());
  };

  const renderStats = () => (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
      <h1 style={{ color: '#fbbf24', textAlign: 'center', marginBottom: '30px' }}>🏆 Tournament Stats</h1>
      
      <h2 style={{ color: '#38bdf8' }}>Points Table</h2>
      <div style={{ overflowX: 'auto', background: '#1e293b', borderRadius: '12px', marginBottom: '40px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#334155', color: 'white' }}>
              <th style={{ padding: '12px', textAlign: 'left' }}>Team</th>
              <th>P</th><th>W</th><th>L</th><th>T</th><th style={{ color: '#fbbf24' }}>Pts</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.points_table.map((t, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #334155', textAlign: 'center' }}>
                <td style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold' }}>{i+1}. {t.team}</td>
                <td>{t.played}</td><td style={{color: '#10b981'}}>{t.won}</td><td style={{color: '#ef4444'}}>{t.lost}</td><td>{t.tied}</td>
                <td style={{ fontWeight: 'bold', color: '#fbbf24', fontSize: '18px' }}>{t.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ color: '#f97316', margin: '0 0 15px 0' }}>🏏 Most Runs</h3>
          {leaderboard.top_batsmen.map((p, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #334155', padding: '10px 0' }}>
              <div><b>{p.name}</b> <span style={{fontSize:'12px', color:'#94a3b8'}}>{p.team__name}</span></div>
              <b style={{ color: '#f97316' }}>{p.runs_scored}</b>
            </div>
          ))}
        </div>

        <div style={{ background: '#1e293b', borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ color: '#a855f7', margin: '0 0 15px 0' }}>🥎 Most Wickets</h3>
          {leaderboard.top_bowlers.map((p, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #334155', padding: '10px 0' }}>
              <div><b>{p.name}</b> <span style={{fontSize:'12px', color:'#94a3b8'}}>{p.team__name}</span></div>
              <b style={{ color: '#a855f7' }}>{p.wickets_taken}</b>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderHome = () => (
    <div style={{ padding: '20px' }}>
      <h1 style={{ color: '#38bdf8', marginBottom: '30px' }}>Live Cricket Tournaments</h1>
      {errorMessage ? (
        <div style={{ background: '#1e293b', padding: '30px', borderRadius: '15px', color: '#fbbf24', fontSize: '18px', maxWidth: '600px', margin: '0 auto', border: '1px solid #ef4444' }}>{errorMessage}</div>
      ) : (
        <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', maxWidth: '1000px', margin: '0 auto' }}>
          {matchList.map(m => (
            <div key={m.id} onClick={() => setSelectedMatchId(m.id)} style={{ background: '#1e293b', padding: '20px', borderRadius: '15px', border: '1px solid #334155', cursor: 'pointer' }}>
              <h3 style={{margin: '10px 0'}}>{m.teams}</h3>
              <button style={{ background: '#38bdf8', border: 'none', padding: '10px 20px', borderRadius: '5px', fontWeight: 'bold', color: '#0f172a' }}>Enter Match</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderToss = () => (
    <div style={{ padding: '20px' }}>
      <button onClick={() => {setSelectedMatchId(null); setMatch(null);}} style={{ marginBottom: '20px', color: '#94a3b8', background: 'none', border: '1px solid #94a3b8', padding: '5px 15px', borderRadius: '5px', cursor: 'pointer' }}>← Back</button>
      <div style={{ background: '#1e293b', padding: '40px', borderRadius: '20px', maxWidth: '400px', margin: '0 auto', boxShadow: '0 10px 25px rgba(0,0,0,0.3)' }}>
        <h2 style={{ color: '#fbbf24', marginTop: 0 }}>🪙 Toss Time</h2>
        <h3 style={{ color: '#fff', marginBottom: '30px' }}>{match.team_a_name} vs {match.team_b_name}</h3>
        
        <label style={{ display: 'block', color: '#94a3b8', textAlign: 'left', marginBottom: '5px' }}>Toss Winner:</label>
        <select value={tossWinner} onChange={(e) => setTossWinner(e.target.value)} style={{ width: '100%', padding: '10px', marginBottom: '20px', background: '#0f172a', color: 'white', border: '1px solid #334155', borderRadius: '8px' }}>
          <option value="">Select Team</option>
          <option value={match.team_a_name}>{match.team_a_name}</option>
          <option value={match.team_b_name}>{match.team_b_name}</option>
        </select>

        <label style={{ display: 'block', color: '#94a3b8', textAlign: 'left', marginBottom: '5px' }}>Elected to:</label>
        <select value={tossDecision} onChange={(e) => setTossDecision(e.target.value)} style={{ width: '100%', padding: '10px', marginBottom: '30px', background: '#0f172a', color: 'white', border: '1px solid #334155', borderRadius: '8px' }}>
          <option value="">Select Decision</option>
          <option value="bat">Bat First</option>
          <option value="bowl">Bowl First</option>
        </select>

        <button onClick={handleTossSubmit} style={{ width: '100%', padding: '12px', background: '#10b981', color: 'white', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '16px' }}>Let's Play!</button>
      </div>
    </div>
  );

  const renderScorecard = () => (
    <div style={{ padding: '20px' }}>
      <button onClick={() => {setSelectedMatchId(null); setMatch(null);}} style={{ marginBottom: '20px', color: '#94a3b8', background: 'none', border: '1px solid #94a3b8', padding: '5px 15px', borderRadius: '5px', cursor: 'pointer' }}>← Back</button>
      
      <div style={{ background: '#1e293b', padding: '30px', borderRadius: '20px', border: match.is_finished ? '3px solid #ef4444' : '3px solid #38bdf8', display: 'inline-block', minWidth: '350px', maxWidth: '500px', boxShadow: '0 10px 25px rgba(0,0,0,0.3)' }}>
        
        <h2 style={{color: '#94a3b8', fontSize: '14px', marginBottom: '5px', textTransform: 'uppercase'}}>{match.team_a_name} <span style={{color: '#334155'}}>VS</span> {match.team_b_name}</h2>
        <div style={{ fontSize: '12px', color: '#fbbf24', marginBottom: '15px', background: 'rgba(251, 191, 36, 0.1)', padding: '5px', borderRadius: '5px' }}>🪙 {match.toss_winner} won the toss and elected to {match.toss_decision}</div>

        {match.is_finished ? (
          <div style={{ background: '#ef4444', color: 'white', padding: '10px', borderRadius: '10px', fontWeight: 'bold', marginBottom: '15px' }}>{match.match_result}</div>
        ) : (
          <div style={{ marginBottom: '15px' }}>
            <span style={{ background: '#10b981', color: '#000', padding: '4px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 'bold', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ height: '8px', width: '8px', background: '#fff', borderRadius: '50%', display: 'inline-block' }}></span>
              🏏 {match.batting_team} IS BATTING ({match.current_innings === 1 ? '1st' : '2nd'} Inn)
            </span>
          </div>
        )}

        <h1 style={{ fontSize: '75px', color: '#fbbf24', marginTop: '10px', marginBottom: '0px', fontWeight: 'bold', lineHeight: '1.1' }}>{match.total_runs} / {match.wickets}</h1>
        <p style={{ fontSize: '20px', color: '#38bdf8', marginTop: '10px', marginBottom: '10px', background: 'rgba(56, 189, 248, 0.1)', padding: '5px 15px', borderRadius: '10px', display: 'inline-block' }}>OVERS: {match.overs}.{match.balls_in_over} ({match.total_overs})</p>

        {match.current_innings === 2 && !match.is_finished && (
          <div style={{ color: '#fbbf24', fontSize: '16px', fontWeight: 'bold', marginBottom: '20px', background: 'rgba(251, 191, 36, 0.1)', padding: '10px', borderRadius: '10px' }}>
            🎯 Target: {match.target_score} <br/> 📉 Needs {match.target_score - match.total_runs} runs in {(match.total_overs * 6) - (match.overs * 6 + match.balls_in_over)} balls
          </div>
        )}
        
        <div ref={scrollRef} style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: '8px', marginBottom: '20px', overflowX: 'auto', padding: '12px 15px', background: '#0f172a', borderRadius: '12px', whiteSpace: 'nowrap', scrollBehavior: 'smooth' }}>
          {match.recent_balls && match.recent_balls.map((ball, index) => (
            <div key={index} style={{ display: 'inline-flex', alignItems: 'center' }}>
              {ball.includes('OV') || ball.includes('=') || ball.includes('TARGET') ? (
                <span style={{ color: ball.includes('=') ? '#10b981' : (ball.includes('TARGET') ? '#fbbf24' : '#38bdf8'), fontWeight: 'bold', fontSize: '14px', margin: '0 10px', padding: '4px 8px', border: ball.includes('=') ? '1px solid #10b981' : 'none', borderRadius: '5px' }}>{ball}</span>
              ) : (
                <div style={{ minWidth: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold', background: ball.includes('W') ? '#ef4444' : (ball.includes('4') || ball.includes('6') ? '#10b981' : '#334155'), color: 'white', border: '1px solid #475569', flexShrink: 0 }}>{ball}</div>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-around', borderTop: '1px solid #334155', paddingTop: '20px' }}>
          <div><p style={{fontSize: '11px', color: '#38bdf8', margin: '0'}}>STRIKER</p><b style={{fontSize: '16px'}}>🏏 {match.current_batsman} *</b><p style={{color: '#fbbf24', fontSize: '18px', fontWeight: 'bold', margin: '5px 0'}}>{match.striker_runs} <span style={{fontSize: '12px', color: '#94a3b8'}}>({match.striker_balls})</span></p></div>
          <div><p style={{fontSize: '11px', color: '#94a3b8', margin: '0'}}>NON-STRIKER</p><b style={{fontSize: '16px'}}>{match.non_striker}</b><p style={{color: '#94a3b8', fontSize: '18px', margin: '5px 0'}}>{match.non_striker_runs} <span style={{fontSize: '12px'}}>({match.non_striker_balls})</span></p></div>
          <div><p style={{fontSize: '11px', color: '#94a3b8', margin: '0'}}>BOWLING</p><b style={{fontSize: '16px'}}>🥎 {match.current_bowler}</b></div>
        </div>

        {!isViewer && !match.is_finished && (
          <div style={{ marginTop: '25px' }}>
            <button onClick={handleUndo} style={{ width: '100%', marginBottom: '20px', padding: '10px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', textTransform: 'uppercase' }}>↩ Undo Last Ball</button>

            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>Select Runs First:</p>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginBottom: '15px' }}>
              {[0,1,2,3,4,6].map(r => (
                <button key={r} onClick={() => setPendingRuns(r)} style={{ width: '40px', height: '40px', background: pendingRuns === r ? '#fbbf24' : '#334155', color: pendingRuns === r ? '#000' : '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer' }}>{r}</button>
              ))}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', marginBottom: '20px' }}>
              <button onClick={() => handleUpdate(pendingRuns)} style={{ background: '#10b981', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Confirm Ball</button>
              <button onClick={() => handleUpdate(pendingRuns, false, 'wide')} style={{ background: '#fbbf24', color: 'black', border: 'none', padding: '10px 15px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>WD</button>
              <button onClick={() => handleUpdate(pendingRuns, false, 'noball')} style={{ background: '#fbbf24', color: 'black', border: 'none', padding: '10px 15px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>NB</button>
              <button onClick={() => handleUpdate(pendingRuns, false, 'legbye')} style={{ background: '#a855f7', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>LB</button>
              <button onClick={() => handleUpdate(0, true)} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '10px 15px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>OUT</button>
            </div>

            <div style={{ background: '#0f172a', padding: '15px', borderRadius: '15px', border: '1px solid #334155' }}>
              <input type="text" value={newPlayerName} onChange={(e)=>setNewPlayerName(e.target.value)} placeholder="Player Name..." style={{ padding: '8px', width: '85%', marginBottom: '10px', background: '#1e293b', border: '1px solid #334155', borderRadius: '5px', color: 'white' }} />
              <div style={{ display: 'flex', gap: '5px', justifyContent: 'center' }}>
                <button onClick={() => handleChangePlayer('striker')} style={{ background: '#10b981', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '5px', fontSize: '11px' }}>Set Striker</button>
                <button onClick={() => handleChangePlayer('non_striker')} style={{ background: '#10b981', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '5px', fontSize: '11px' }}>Set Non-Stk</button>
                <button onClick={() => handleChangePlayer('bowler')} style={{ background: '#6366f1', color: 'white', border: 'none', padding: '6px 10px', borderRadius: '5px', fontSize: '11px' }}>Set Bowler</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ marginTop: '40px', maxWidth: '600px', margin: '40px auto', textAlign: 'left', padding: '0 10px' }}>
        <h3 style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '10px' }}>Batter ↓</h3>
        <div style={{ overflowX: 'auto', background: '#1e293b', borderRadius: '12px', marginBottom: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ background: '#334155', color: '#38bdf8' }}>
                <th style={{ padding: '12px', textAlign: 'left' }}>Player</th>
                <th>R</th><th>B</th><th>4s</th><th>6s</th><th>S.R</th>
              </tr>
            </thead>
            <tbody>
              {match.batting_card?.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '12px' }}>
                    <div style={{ fontWeight: 'bold' }}>{p.name} {p.name === match.current_batsman ? '*' : ''}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>{p.name === match.current_batsman || p.name === match.non_striker ? 'Not out' : 'Out'}</div>
                  </td>
                  <td style={{ textAlign: 'center', fontWeight: 'bold' }}>{p.runs_scored}</td>
                  <td style={{ textAlign: 'center' }}>{p.balls_faced}</td>
                  <td style={{ textAlign: 'center' }}>{p.fours}</td>
                  <td style={{ textAlign: 'center' }}>{p.sixes}</td>
                  <td style={{ textAlign: 'center', color: '#94a3b8' }}>{p.balls_faced > 0 ? ((p.runs_scored / p.balls_faced) * 100).toFixed(1) : '0.0'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ backgroundColor: '#0f172a', minHeight: '100vh', color: 'white', textAlign: 'center', fontFamily: 'Arial, sans-serif' }}>
      {!selectedMatchId && (
        <div style={{ background: '#1e293b', padding: '15px', display: 'flex', justifyContent: 'center', gap: '20px', borderBottom: '1px solid #334155' }}>
          <button onClick={() => setActiveTab('matches')} style={{ background: activeTab === 'matches' ? '#38bdf8' : 'transparent', color: activeTab === 'matches' ? '#0f172a' : 'white', border: '1px solid #38bdf8', padding: '8px 20px', borderRadius: '20px', fontWeight: 'bold', cursor: 'pointer' }}>Live Matches</button>
          <button onClick={() => setActiveTab('stats')} style={{ background: activeTab === 'stats' ? '#fbbf24' : 'transparent', color: activeTab === 'stats' ? '#0f172a' : 'white', border: '1px solid #fbbf24', padding: '8px 20px', borderRadius: '20px', fontWeight: 'bold', cursor: 'pointer' }}>Points Table & Stats</button>
        </div>
      )}

      {!selectedMatchId ? (
        activeTab === 'matches' ? renderHome() : renderStats()
      ) : (
        match ? ( (!match.toss_winner && !isViewer) ? renderToss() : renderScorecard() ) : <h2 style={{marginTop: '50px', color: '#38bdf8'}}>Loading Match Data...</h2>
      )}
    </div>
  );
}

export default App;