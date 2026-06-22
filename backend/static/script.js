const BASE_URL = "";

async function registerOrg() {
    const name = document.getElementById("orgName").value;

    // Quick check to make sure they didn't leave it blank
    if (!name) {
        alert("Please enter an organization name.");
        return;
    }

    try {
        const res = await fetch(BASE_URL + "/orgs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name })
        });

        // Parse the data from the backend FIRST, before checking if it failed
        const data = await res.json();

        // Now we check if the backend gave us a green light (200 OK)
        if (res.ok) {
            alert("✅ " + data.message);
            document.getElementById("orgName").value = ""; // Clear the box
        } else {
            // If it's a 400 error, show the EXACT message Python sent!
            alert("❌ " + data.error);
        }

    } catch (err) {
        // This only triggers if the Flask server is completely turned off
        console.error("Network error:", err);
        alert("❌ Error: Could not connect to the backend server.");
    }
}

async function submitCTI() {
    const ctiData = document.getElementById("ctiData").value;
    const orgName = document.getElementById("submitterOrgName").value;
    const threatType = document.getElementById("threatType").value; // Grab threat type

    if (!ctiData || !orgName) {
        alert("Please enter all fields.");
        return;
    }

    const res = await fetch(BASE_URL + "/cti", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            cti_data: ctiData, 
            org_name: orgName,
            threat_type: threatType // Send to Python
        }) 
    });

    const data = await res.json();
    alert(data.message || data.error);
}

async function loadThreatFeed() {
    const orgName = document.getElementById("viewerOrgName").value;
    const feedContainer = document.getElementById("ctiFeed");

    if (!orgName) {
        alert("Please enter your Organization Name to access the feed.");
        return;
    }

    try {
        // Send the name to the backend for verification
        const res = await fetch(`${BASE_URL}/cti?org_name=${encodeURIComponent(orgName)}`);
        const data = await res.json();

        // Check if the backend blocked us (403 or 400 error)
        if (!res.ok) {
            alert(data.error); 
            feedContainer.innerHTML = ""; // Keep feed hidden
            return;
        }

        // If access is granted, build the feed!
        feedContainer.innerHTML = `<h3 style="color: #00ffcc;">🔓 Access Granted for ${orgName}</h3>`;
        
        data.forEach(threat => {
            const isUnchanged = threat.integrity_status === "Unchanged";
            const statusColor = isUnchanged ? "#00ffcc" : "#ff4444"; 
            const statusIcon = isUnchanged ? "✅" : "❌";

            // --- NEW: Logic to display stars or "Unrated" ---
            let starDisplay = "";
            // If the rating is 0 or missing, show Unrated
            if (!threat.average_rating || threat.average_rating === 0) {
                starDisplay = "<span style='color: #888; font-style: italic;'>Unrated (0)</span>";
            } else {
                // Repeat the star emoji based on the score! (e.g., 4 = ⭐⭐⭐⭐)
                starDisplay = "⭐".repeat(threat.average_rating) + ` <span style='font-size: 0.8em; color: #ccc;'>(${threat.average_rating}/5)</span>`;
            }

            const threatHTML = `
                <div style="border: 1px solid #444; padding: 15px; margin-top: 10px; border-radius: 5px; background-color: #1a1a1a; position: relative;">
                    <div style="position: absolute; top: 10px; right: 15px; color: #ffeb3b; font-weight: bold; font-size: 1.1em;">
                        CTI ID: #${threat.cti_id}
                    </div>

                    <p style="margin: 0 0 10px 0;"><strong>🏢 Reported By:</strong> ${threat.orgName}</p>
                    <p style="margin: 0 0 5px 0;"><strong>🚨 Threat Type:</strong> ${threat.threatType}</p>
                    
                    <p style="margin: 0 0 10px 0;"><strong>🏆 Community Rating:</strong> ${starDisplay}</p>
                    
                    <p style="margin: 0 0 15px 0;"><strong>📝 Data:</strong> <span style="font-family: monospace;">${threat.payload.indicators}</span></p>
                    <p style="margin: 0; color: ${statusColor}; font-weight: bold;">
                        ${statusIcon} Data Integrity: ${threat.integrity_status}
                    </p>
                </div>
            `;
            feedContainer.innerHTML += threatHTML;
        });

    } catch (error) {
        console.error("Error loading feed:", error);
    }
}

async function rateCTI() {
    const orgName = document.getElementById("raterOrgName").value;
    const ctiId = document.getElementById("targetCtiId").value;
    const rating = document.getElementById("ratingScore").value;

    if (!orgName || !ctiId || !rating) {
        alert("Please fill in all fields.");
        return;
    }

    const res = await fetch(BASE_URL + "/rate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
            rater_org_name: orgName, 
            cti_id: parseInt(ctiId), // Ensure it sends as a number
            rating: parseInt(rating) 
        })
    });

    const data = await res.json();
    if (res.ok) {
        alert("✅ " + data.message);
        // --- NEW: Clear the form inputs for a better user experience ---
        document.getElementById("targetCtiId").value = "";
        document.getElementById("ratingScore").value = "";
        
        // --- NEW: Automatically refresh the live feed! ---
        loadThreatFeed();
    } else {
        alert("❌ Error: " + data.error);
    }
}

async function loadLeaderboard() {
    // 1. Grab the organization name
    const orgName = document.getElementById("leaderboardViewerName").value;
    const feed = document.getElementById("leaderboardFeed");

    // 2. Stop them if they leave it blank
    if (!orgName) {
        alert("Please enter your Organization Name to unlock the leaderboard.");
        return;
    }

    feed.innerHTML = "<p style='color: #00ffcc;'>Verifying access and fetching data...</p>";

    try {
        // 3. Send the name to the backend for verification
        const res = await fetch(`${BASE_URL}/leaderboard?org_name=${encodeURIComponent(orgName)}`);
        const data = await res.json();

        // 4. Handle the Access Denied error from Python
        if (!res.ok) {
            feed.innerHTML = `<p style="color: #ff4444;">❌ ${data.error}</p>`;
            return;
        }

        feed.innerHTML = ""; // Clear the loading text
        
        if (data.length === 0) {
            feed.innerHTML = "<p style='color: #888;'>No organizations registered yet.</p>";
            return;
        }

        // 5. Draw the Leaderboard!
        data.forEach((org, index) => {
            let rank = `#${index + 1}`;
            if (index === 0) rank = "🥇 1st";
            if (index === 1) rank = "🥈 2nd";
            if (index === 2) rank = "🥉 3rd";

            const stars = org.score === 0 ? "<span style='color: #888;'>Unrated</span>" : "⭐".repeat(org.score);

            const orgHTML = `
                <div style="border-bottom: 1px solid #333; padding: 12px 0; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 1.1em; color: #fff;">
                        <span style="color: #00ffcc; width: 80px; display: inline-block;">${rank}</span> 
                        ${org.name}
                    </span>
                    <span style="font-size: 1.2em;">${stars}</span>
                </div>
            `;
            feed.innerHTML += orgHTML;
        });

    } catch (error) {
        console.error("Leaderboard fetch error:", error);
        feed.innerHTML = "<p style='color: #ff4444;'>Failed to connect to backend.</p>";
    }
}
