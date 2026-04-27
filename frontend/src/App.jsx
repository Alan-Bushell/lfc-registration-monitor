import React, { useState, useEffect } from 'react';

// Use relative path in production (same domain), or Codespaces domain for dev
const API_URL = import.meta.env.VITE_API_URL || "";
console.log("Configured API URL:", API_URL);

function App() {
  const [user, setUser] = useState(null);

    const refreshStatus = async (userId) => {
        try {
            const res = await fetch(`${API_URL}/auth/status/${userId}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.user) setUser(data);
        } catch (error) {
            console.error("Status refresh error:", error);
        }
    };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
        const success = params.get("success");
        const canceled = params.get("canceled");
        const storedUserId = window.localStorage.getItem("userId");
    
    if (code) {
      fetch(`${API_URL}/auth/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code })
      })
      .then(res => res.json())
      .then(data => {
          if (data.user) {
              setUser(data);
                            window.localStorage.setItem("userId", data.id);
                            window.localStorage.setItem("userEmail", data.user);
              window.history.replaceState({}, document.title, "/");
          }
      })
      .catch(err => console.error(err));
        } else if (storedUserId) {
            refreshStatus(storedUserId);
        }

        if (success || canceled) {
            if (storedUserId) {
                refreshStatus(storedUserId);
            }
            window.history.replaceState({}, document.title, "/");
    }
  }, []);

  const handleLogin = async () => {
    try {
        console.log("Fetching from:", `${API_URL}/auth/login`);
        const res = await fetch(`${API_URL}/auth/login`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        window.location.href = data.url;
    } catch (error) {
        console.error("Login error:", error);
        alert(`Backend error: ${error.message}. Check browser console. Configured URL: ${API_URL}`);
    }
  };

  const handleSubscribe = async () => {
    if (!user) return;
    try {
        console.log("Calling Stripe checkout with:", user);
        const res = await fetch(`${API_URL}/stripe/checkout-session`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: user.user }) 
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.url) window.location.href = data.url;
    } catch (error) {
        console.error("Stripe error:", error);
        alert(`Payment error: ${error.message}. URL: ${API_URL}`);
    }
  };

    const handleManageSubscription = async () => {
        if (!user) return;
        try {
            const res = await fetch(`${API_URL}/stripe/customer-portal`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: user.user })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data.url) window.location.href = data.url;
        } catch (error) {
            console.error("Portal error:", error);
            alert(`Portal error: ${error.message}. URL: ${API_URL}`);
        }
    };

  return (
    <>
      <div className="container">
        <header>
          <a href="/" className="logo">
            Fut<span>Cal</span>
          </a>
          <nav>
            {!user ? (
                <button onClick={handleLogin} className="btn btn-secondary">
                    Sign In
                </button>
            ) : (
                <span className="user-email" style={{ color: '#94a3b8' }}>{user.user}</span>
            )}
          </nav>
        </header>

        <main>
            {!user ? (
                <>
                <div className="hero">
                    <h1>Never miss a <br/><span>Registration Window</span> again.</h1>
                    <p>
                        We monitor the "Additional Members Sales" so you don't have to. 
                        Get the exact date and time for sales added directly to your Google Calendar.
                    </p>
                    <div style={{ marginTop: '2.5rem' }}>
                        <button onClick={handleLogin} className="btn btn-primary">
                            Begin Setup
                        </button>
                    </div>

                    <div className="disclaimer" style={{ maxWidth: '500px', fontSize: '0.85rem', padding: '0.75rem' }}>
                        ⚠️ <strong>Note:</strong> We provide alerts, not tickets. Purchasing is first-come, first-served via the official club portal.
                    </div>
                </div>

                <div className="features-grid" style={{ marginBottom: '4rem' }}>
                     <div className="feature-card">
                        <h3>Your Calendar, Automated</h3>
                        <p style={{ marginBottom: '1.5rem' }}>
                            For every home game, we automatically create two distinct events in your calendar:
                        </p>
                        <ul style={{ textAlign: 'left', color: '#ccc', listStyle: 'none', padding: 0 }}>
                            <li style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '1.2rem' }}>📝</span> 
                                <div>
                                    <strong style={{ color: '#fff' }}>Registration Window</strong>
                                    <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>Reminds you to register interest before the deadline.</div>
                                </div>
                            </li>
                            <li style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <span style={{ fontSize: '1.2rem' }}>🎟️</span>
                                <div>
                                    <strong style={{ color: '#fff' }}>Ticket Sale</strong>
                                    <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>The actual sale time. Includes direct link to the booking page.</div>
                                </div>
                            </li>
                        </ul>
                    </div>
                    <div className="feature-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                         <div style={{ background: '#1a1a1a', padding: '1.5rem', borderRadius: '12px', border: '1px solid #333', textAlign: 'left', position: 'relative' }}>
                            <div style={{ position: 'absolute', top: '-10px', right: '20px', background: '#C8102E', color: 'white', fontSize: '0.7rem', fontWeight: 'bold', padding: '2px 8px', borderRadius: '4px' }}>CALENDAR EVENT</div>
                            <div style={{ color: '#F6EB61', fontSize: '0.85rem', fontWeight: 'bold' }}>TOMORROW • 08:00 - 09:00</div>
                            <h4 style={{ margin: '5px 0', fontSize: '1.1rem', color: 'white' }}>LFC v Man City - Registration</h4>
                            <div style={{ fontSize: '0.9rem', color: '#999', marginTop: '10px' }}>
                                🔗 <u>https://liverpoolfc.com/tickets...</u>
                            </div>
                        </div>
                        <p style={{ marginTop: '1.5rem', fontSize: '0.9rem' }}>*Example of what you'll see on your phone.</p>
                    </div>
                </div>

                <div className="hero" style={{ padding: '2rem 0', textAlign: 'left' }}>
                    <h2 style={{ fontSize: '2.5rem', marginBottom: '2rem', textAlign: 'center' }}>How It Works</h2>
                    <div className="features-grid">
                        <div className="feature-card">
                            <h3 style={{ color: '#F6EB61' }}>1. Connect</h3>
                            <p>Sign in with Google. We only ask for permission to add these specific events to your calendar.</p>
                        </div>
                        <div className="feature-card">
                            <h3 style={{ color: '#F6EB61' }}>2. Automate</h3>
                            <p>Our bots scan the official website 24/7 so you don't have to. No more wasting time checking multiple times a day.</p>
                        </div>
                        <div className="feature-card">
                            <h3 style={{ color: '#F6EB61' }}>3. Secure</h3>
                            <p>Get the calendar alert instantly. Click the direct link, join the queue, and give yourself the best chance of securing a seat.</p>
                        </div>
                    </div>
                </div>
                </>
            ) : (
                <div className="dashboard-container">
                    <div className="hero" style={{ padding: '2rem 0', textAlign: 'left'}}>
                        <h1>Welcome back.</h1>
                        <p style={{ margin: 0 }}>Your automation dashboard.</p>
                    </div>

                    <div className="dashboard-card">
                        <h3 style={{ color: '#9aa0a6' }}>Subscription Status</h3>
                        
                        <div style={{ margin: '1.5rem 0'}}>
                            <span className={`status-indicator ${user.status === 'active' ? 'active' : 'inactive'}`}>
                                {user.status === 'active' ? 'ACTIVE' : 'INACTIVE'}
                            </span>
                        </div>
                        
                        {user.status === 'active' ? (       
                            <div style={{ textAlign: 'left', marginTop: '2rem', borderTop: '1px solid #333', paddingTop: '2rem' }}>
                                <p style={{ color: '#F6EB61', fontWeight: 'bold', fontSize: '1.2rem' }}>✅ Monitoring Active</p>
                                <p>Your calendar is connected. We will auto-add events as they are found manually.</p>
                                <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginTop: '1rem' }}>Next scan in: ~45 mins</p>
                                <button onClick={handleManageSubscription} className="btn btn-secondary" style={{ marginTop: '1.5rem' }}>
                                    Manage Subscription
                                </button>
                            </div>
                        ) : (
                            <div>
                                <p style={{ marginBottom: '2rem' }}>Activate your subscription to start receiving calendar invites.</p>
                                <div style={{ background: '#0a0a0a', padding: '2rem', borderRadius: '12px', border: '1px solid #C8102E' }}>
                                    <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem', color: '#fff' }}>€29.99<small style={{ fontSize: '1rem', color: '#94a3b8', marginLeft: '5px' }}>/ year</small></h2>
                                    <button onClick={handleSubscribe} className="btn btn-primary" style={{ width: '100%', marginTop: '1.5rem' }}>
                                        Subscribe with Stripe
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </main>

        <footer>
            <p>&copy; {new Date().getFullYear()} FutCal. Not affiliated with Liverpool Football Club.</p>
            <p style={{ fontSize: '0.8rem', color: '#444' }}>Terms • Privacy • Support</p>
        </footer>
      </div>
    </>
  );
}

export default App;
