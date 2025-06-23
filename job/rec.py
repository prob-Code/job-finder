"""
Google Jobs API Recommendation System
Fetches jobs from Google Jobs via SerpAPI and provides recommendations
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
from math import radians, sin, cos, sqrt, atan2

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key (Replace with your SerpAPI key)
SERPAPI_KEY = "2c5ad5a55eb1534200cfaea4df2b8236ae221f6c403eeb82ae05383a3884e733"

class JobFinder:
    def __init__(self):
        self.jobs = []
    
    def fetch_google_jobs(self, query, location, country="us"):
        """Fetch jobs from Google Jobs API via SerpAPI"""
        url = f"https://serpapi.com/search.json?engine=google_jobs"
        params = {
            "q": query,
            "location": location,
            "hl": "en",
            "api_key":"2c5ad5a55eb1534200cfaea4df2b8236ae221f6c403eeb82ae05383a3884e733",
            "country": country
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for job in data.get("jobs_results", []):
                jobs.append({
                    "title": job.get("title", "No title"),
                    "company": job.get("company_name", "Unknown company"),
                    "location": job.get("location", "Unknown location"),
                    "description": job.get("description", ""),
                    "posted_date": job.get("detected_extensions", {}).get("posted_at", "Unknown"),
                    "job_type": job.get("job_type", "Unknown"),
                    "apply_url": job.get("related_links", [{}])[0].get("link", "#"),
                    "remote": "remote" in job.get("location", "").lower()
                })
            return jobs
        except Exception as e:
            logger.error(f"Error fetching Google Jobs: {e}")
            return []

    def score_jobs(self, jobs, skills, user_location):
        """Score jobs based on skills and location"""
        scored_jobs = []
        
        for job in jobs:
            # Skill matching (basic keyword matching)
            job_text = (job["title"] + " " + job["description"]).lower()
            skill_score = sum(skill.lower() in job_text for skill in skills) / len(skills) if skills else 0
            
            # Location scoring
            if job["remote"]:
                location_score = 1.0
            else:
                location_score = 0.7 if user_location.lower() in job["location"].lower() else 0.3
            
            # Combined score (70% skills, 30% location)
            total_score = (skill_score * 0.7) + (location_score * 0.3)
            
            if total_score > 0.2:  # Minimum threshold
                job["score"] = round(total_score, 2)
                scored_jobs.append(job)
        
        # Sort by score (highest first)
        return sorted(scored_jobs, key=lambda x: x["score"], reverse=True)

# Initialize Job Finder
job_finder = JobFinder()

# API Endpoint
@app.route('/api/jobs', methods=['GET', 'POST'])
def get_jobs():
    try:
        # Get parameters from request
        if request.method == 'POST':
            data = request.get_json()
            query = data.get("query", "software engineer")
            location = data.get("location", "New York")
            skills = data.get("skills", [])
        else:  # GET request
            query = request.args.get("query", "software engineer")
            location = request.args.get("location", "New York")
            skills = request.args.get("skills", "")
            skills = [s.strip() for s in skills.split(",")] if skills else []
        
        # Fetch jobs from Google Jobs API
        jobs = job_finder.fetch_google_jobs(query, location)
        
        # Score and filter jobs
        scored_jobs = job_finder.score_jobs(jobs, skills, location)
        
        return jsonify({
            "status": "success",
            "jobs": scored_jobs[:50],  # Return top 50
            "count": len(scored_jobs)
        })
    except Exception as e:
        logger.error(f"Error in /api/jobs: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Minimal Frontend
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Jobs Finder</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .search-box { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            input, button { padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; }
            button { background: #4285F4; color: white; border: none; cursor: pointer; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            .job { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
            .job h3 { margin-top: 0; color: #202124; }
            .job p { color: #5f6368; margin: 5px 0; }
            .score { color: #0f9d58; font-weight: bold; }
            #results { margin-top: 20px; }
            #loading { display: none; text-align: center; }
        </style>
    </head>
    <body>
        <h1>Google Jobs Finder</h1>
        <div class="search-box">
            <input type="text" id="query" placeholder="Job title" value="Software Engineer">
            <input type="text" id="location" placeholder="Location" value="New York">
            <input type="text" id="skills" placeholder="Skills (comma separated)">
            <button onclick="searchJobs()">Search Jobs</button>
        </div>
        <div id="loading">Loading jobs...</div>
        <div id="results"></div>

        <script>
            async function searchJobs() {
                const query = document.getElementById('query').value;
                const location = document.getElementById('location').value;
                const skills = document.getElementById('skills').value;

                document.getElementById('results').innerHTML = '';
                document.getElementById('loading').style.display = 'block';

                try {
                    const response = await fetch('/api/jobs', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query, location, skills: skills.split(',').map(s => s.trim()) })
                    });

                    const data = await response.json();
                    document.getElementById('loading').style.display = 'none';

                    if (data.status === 'error') throw new Error(data.message);

                    let html = '';
                    data.jobs.forEach((job, index) => {
                        html += `
                            <div class="job">
                                <h3>${job.title}</h3>
                                <p><strong>${job.company}</strong> • ${job.location}</p>
                                <p>${job.description.slice(0, 150)}...</p>
                                <p>Posted: ${job.posted_date} • <span class="score">Match: ${(job.score * 100).toFixed(0)}%</span></p>
                                <button onclick="markAsApplied(${index})" id="apply-btn-${index}">Apply Now</button>
                            </div>
                        `;
                    });

                    document.getElementById('results').innerHTML = 
                        `<h2>Found ${data.count} jobs</h2>` + (html || '<p>No jobs found</p>');
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('results').innerHTML = 
                        `<p style="color:red">Error: ${error.message}</p>`;
                }
            }

            function markAsApplied(index) {
                const btn = document.getElementById(`apply-btn-${index}`);
                btn.textContent = "Applied ✅";
                btn.disabled = true; 
            }
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


