"""
Lightweight recruiter dashboard on top of the FastAPI backend — post a job,
run a candidate through the pipeline, watch the agent trace, and run
semantic search across the candidate pool.

Run with:
    streamlit run streamlit_app.py

(requires the API running separately: `uvicorn app.main:app --reload`)
"""
import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="TalentFlow AI", page_icon="🧑‍💼", layout="wide")
st.title("🧑‍💼 TalentFlow AI — Recruiter Dashboard")

tab_pipeline, tab_search, tab_jobs = st.tabs(["Run Pipeline", "Semantic Search", "Post a Job"])

with tab_jobs:
    st.subheader("Post a new job")
    with st.form("job_form"):
        title = st.text_input("Job title", "Backend Engineer")
        description = st.text_area("Job description", "5+ years Python, FastAPI, PostgreSQL, distributed systems.")
        skills = st.text_input("Required skills (comma-separated)", "python, fastapi, postgresql")
        submitted = st.form_submit_button("Create job")
        if submitted:
            resp = requests.post(f"{API_BASE}/api/jobs", json={
                "title": title,
                "description": description,
                "required_skills": [s.strip() for s in skills.split(",") if s.strip()],
            })
            if resp.ok:
                st.success(f"Created job #{resp.json()['id']}: {title}")
            else:
                st.error(resp.text)

    st.subheader("Existing jobs")
    jobs_resp = requests.get(f"{API_BASE}/api/jobs")
    if jobs_resp.ok:
        for job in jobs_resp.json():
            st.write(f"**#{job['id']} — {job['title']}**: {', '.join(job['required_skills'])}")

with tab_pipeline:
    st.subheader("Run a candidate through the pipeline")
    job_id = st.number_input("Job ID", min_value=1, step=1, value=1)
    name = st.text_input("Candidate name (optional)")
    email = st.text_input("Candidate email (optional)")
    resume_text = st.text_area("Resume text", height=200,
                                placeholder="Paste resume text here...")

    if st.button("Run pipeline", type="primary"):
        with st.spinner("Running agents..."):
            resp = requests.post(f"{API_BASE}/api/pipeline/run", json={
                "job_id": job_id,
                "resume_text": resume_text,
                "name": name or None,
                "email": email or None,
            })
        if resp.ok:
            data = resp.json()
            st.success(f"Final stage: **{data['final_stage']}**")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Screening score", f"{data['screening']['overall_score']:.2f}")
                st.write("Matched skills:", ", ".join(data['screening']['matched_skills']) or "—")
                st.write("Missing skills:", ", ".join(data['screening']['missing_skills']) or "—")
            with col2:
                if data.get("decision"):
                    st.metric("Recommendation", data["decision"]["recommendation"])
                    st.write(data["decision"]["rationale"])
                    if data["decision"].get("bias_warning"):
                        st.warning(data["decision"]["bias_warning"])

            st.subheader("Agent trace")
            st.json(data["trace"])
        else:
            st.error(resp.text)

with tab_search:
    st.subheader("Semantic candidate search (FAISS)")
    query = st.text_input("Describe who you're looking for",
                           "backend engineer with distributed systems experience")
    top_k = st.slider("Results", 1, 10, 5)
    if st.button("Search"):
        resp = requests.get(f"{API_BASE}/api/candidates/search", params={"query": query, "top_k": top_k})
        if resp.ok:
            results = resp.json()
            if not results:
                st.info("No candidates indexed yet — run the pipeline on a few resumes first.")
            for r in results:
                st.write(f"**{r['candidate']['name'] or 'Unnamed'}** (candidate #{r['candidate']['candidate_id']}) — similarity {r['score']:.3f}")
        else:
            st.error(resp.text)
