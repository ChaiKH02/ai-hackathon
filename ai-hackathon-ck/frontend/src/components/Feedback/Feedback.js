import React, { useState, useEffect } from 'react';
import {
    MessageSquare, ThumbsUp, ThumbsDown, TrendingUp,
    Filter, Download, Loader, Calendar, Layers
} from 'lucide-react';
import './Feedback.css';

const API_URL = process.env.REACT_APP_BACKEND_API_URL;

const Feedback = () => {
    // --- 1. Configuration ---
    const departments = ['All', 'IT', 'HR', 'Sales', 'Finance', 'Engineering', 'Marketing'];
    const quarters = ['All', 'Q1', 'Q2', 'Q3', 'Q4'];
    const sentiments = ['All', 'Positive', 'Negative', 'Neutral'];

    // Dynamic Year Generation (Last 5 Years)
    const currentYear = new Date().getFullYear();
    const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

    // --- 2. State Management ---
    // Filters
    const [selectedDept, setSelectedDept] = useState('All');
    const [selectedYear, setSelectedYear] = useState(currentYear);
    const [selectedQuarter, setSelectedQuarter] = useState('All');
    const [selectedSentiment, setSelectedSentiment] = useState('All');

    // Data
    const [metrics, setMetrics] = useState({
        totalFeedbackCount: 0,
        positiveCount: 0,
        negativeCount: 0,
        detectedThemes: 0
    });
    const [themes, setThemes] = useState([]);
    const [recentFeedback, setRecentFeedback] = useState([]);

    // UI State
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [periodLabel, setPeriodLabel] = useState("");

    // --- 3. Helpers ---
    const getIconForCategory = (category) => {
        if (!category) return '📊';
        const cat = category.toLowerCase();
        if (cat.includes('workload') || cat.includes('capacity')) return '💼';
        if (cat.includes('recogni') || cat.includes('reward')) return '🏆';
        if (cat.includes('leader') || cat.includes('manage')) return '👔';
        if (cat.includes('career') || cat.includes('growth')) return '🎯';
        if (cat.includes('collab') || cat.includes('team')) return '🤝';
        if (cat.includes('balance') || cat.includes('life')) return '⚖️';
        if (cat.includes('innovat') || cat.includes('creat')) return '💡';
        if (cat.includes('culture') || cat.includes('environ')) return '🌟';
        return '📊';
    };

    // --- 4. Main Data Fetching Logic ---
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                // Construct Query Params
                const params = new URLSearchParams();
                if (selectedYear) params.append('year', selectedYear);
                if (selectedDept !== 'All') params.append('department', selectedDept);
                if (selectedQuarter !== 'All') params.append('quarter', selectedQuarter);
                if (selectedSentiment !== 'All') params.append('sentiment_label', selectedSentiment);

                // Fetch Insights & Recent Feedback in parallel
                const [insightsResponse, feedbackResponse] = await Promise.all([
                    fetch(`${API_URL}/theme/insights?${params.toString()}&limit=8`),
                    fetch(`${API_URL}/theme/recent-feedback?${params.toString()}&limit=5`)
                ]);

                if (!insightsResponse.ok || !feedbackResponse.ok) {
                    throw new Error('Failed to fetch data from server');
                }

                const rawInsights = await insightsResponse.json();
                const rawFeedback = await feedbackResponse.json();

                // A. Handle "Comparison" Label (e.g., "vs prev Q")
                const periodType = rawInsights.period_compared;
                let pLabel = "";
                if (periodType === 'Quarter' && selectedQuarter !== 'All') {
                    pLabel = "vs prev Q";
                } else if (periodType === 'Year') {
                    pLabel = "vs prev Year";
                }
                setPeriodLabel(pLabel);

                // B. Set Global Metrics (Directly from API calculations)
                const globalSentiments = rawInsights.global_sentiment || { Positive: 0, Negative: 0 };
                setMetrics({
                    totalFeedbackCount: rawInsights.total_responses_processed || 0,
                    positiveCount: globalSentiments.Positive || 0,
                    negativeCount: globalSentiments.Negative || 0,
                    detectedThemes: rawInsights.total_themes_detected || 0
                });

                // C. Process Themes List
                processThemeList(rawInsights.data);

                // D. Set Recent Feedback
                setRecentFeedback(rawFeedback.data || []);

            } catch (err) {
                console.error("Error fetching feedback data:", err);
                setError("Failed to load dashboard data.");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [selectedDept, selectedYear, selectedQuarter, selectedSentiment]);

    // --- 5. Theme Processing (UI Mapping) ---
    const processThemeList = (data) => {
        if (!data || data.length === 0) {
            setThemes([]);
            return;
        }

        // Find max count for progress bar scaling
        const maxCount = Math.max(...data.map(i => Number(i.response_count) || 0));

        const mappedThemes = data.map((item, index) => {
            // Logic: Find the most significant metric change (Diff)
            const insights = item.insights || {};

            const metricMap = [
                { key: 'avg_job_satisfaction_diff', label: 'Satisfaction' },
                { key: 'avg_work_life_balance_diff', label: 'WLB' },
                { key: 'avg_manager_support_diff', label: 'Support' },
                { key: 'avg_enps_diff', label: 'eNPS' }
            ];

            let maxDiffVal = 0;
            let maxDiffLabel = "Stable";

            metricMap.forEach(m => {
                const val = insights[m.key];
                // Check if this metric has a larger absolute change than the current max
                if (val !== undefined && Math.abs(val) > Math.abs(maxDiffVal)) {
                    maxDiffVal = val;
                    maxDiffLabel = m.label;
                }
            });

            // Format Trend String
            const isSignificant = Math.abs(maxDiffVal) > 0;
            const trendText = isSignificant
                ? `${maxDiffLabel} ${maxDiffVal > 0 ? '+' : ''}${maxDiffVal}`
                : "No Change";

            const trendDirection = maxDiffVal > 0 ? 'up' : maxDiffVal < 0 ? 'down' : 'flat';

            return {
                id: index,
                icon: getIconForCategory(item.category),
                title: item.category,
                mentions: Number(item.response_count),
                // Calculate percentage relative to the top theme
                impact: maxCount > 0 ? Math.round((Number(item.response_count) / maxCount) * 100) : 0,
                // Color coding based on dominant sentiment
                color: (item.dominant_sentiment || '').toLowerCase() === 'negative' ? '#ef4444' :
                    (item.dominant_sentiment || '').toLowerCase() === 'positive' ? '#10b981' : '#f59e0b',

                trendDirection: trendDirection,
                trendValue: trendText
            };
        });

        setThemes(mappedThemes);
    };

    if (error) return <div className="feedback-container"><div className="error-message">{error}</div></div>;

    return (
        <div className="feedback-container">
            {/* --- Header --- */}
            <div className="feedback-header">
                <div>
                    <h1 className="page-title">Feedback Analysis</h1>
                    <p className="page-subtitle">
                        Analyzing <strong>{selectedDept}</strong> during <strong>{selectedQuarter === 'All' ? 'Full Year' : selectedQuarter} {selectedYear}</strong>
                    </p>
                </div>
                <button className="export-btn">
                    <Download size={16} />
                    Export Report
                </button>
            </div>

            {/* --- Filters Bar --- */}
            <div className="filter-bar-modern">
                <div className="filters-wrapper">
                    <div className="filter-label-group">
                        <Filter size={20} color="var(--text-secondary)" />
                        <span>Filters:</span>
                    </div>

                    <div className="select-wrapper">
                        <select className="filter-select-modern" value={selectedDept} onChange={(e) => setSelectedDept(e.target.value)}>
                            {departments.map(d => <option key={d} value={d}>{d === 'All' ? 'All Departments' : d}</option>)}
                        </select>
                    </div>

                    <div className="select-wrapper">
                        <Calendar size={16} className="select-icon" />
                        <select className="filter-select-modern with-icon" value={selectedYear} onChange={(e) => setSelectedYear(Number(e.target.value))}>
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                    </div>

                    <div className="select-wrapper">
                        <Layers size={16} className="select-icon" />
                        <select className="filter-select-modern with-icon" value={selectedQuarter} onChange={(e) => setSelectedQuarter(e.target.value)}>
                            {quarters.map(q => <option key={q} value={q}>{q === 'All' ? 'All Quarters' : q}</option>)}
                        </select>
                    </div>

                    <div className="select-wrapper">
                        <select className="filter-select-modern" value={selectedSentiment} onChange={(e) => setSelectedSentiment(e.target.value)}>
                            {sentiments.map(s => <option key={s} value={s}>{s === 'All' ? 'All Sentiments' : s}</option>)}
                        </select>
                    </div>
                </div>
            </div>

            {/* --- Loading State --- */}
            {loading ? (
                <div className="loading-container">
                    <Loader className="animate-spin" size={40} color="var(--primary)" />
                    <p>Analyzing feedback data...</p>
                </div>
            ) : (
                <>
                    {/* --- Metrics Grid --- */}
                    <div className="metrics-grid">
                        <div className="metric-card">
                            <div className="metric-icon" style={{ backgroundColor: '#3b82f615' }}>
                                <MessageSquare size={24} color="#3b82f6" />
                            </div>
                            <div className="metric-content">
                                <div className="metric-value">{metrics.totalFeedbackCount}</div>
                                <div className="metric-label">Total Feedbacks</div>
                            </div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-icon" style={{ backgroundColor: '#10b98115' }}>
                                <ThumbsUp size={24} color="#10b981" />
                            </div>
                            <div className="metric-content">
                                <div className="metric-value">{metrics.positiveCount}</div>
                                <div className="metric-label">Positive Feedbacks</div>
                            </div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-icon" style={{ backgroundColor: '#ef444415' }}>
                                <ThumbsDown size={24} color="#ef4444" />
                            </div>
                            <div className="metric-content">
                                <div className="metric-value">{metrics.negativeCount}</div>
                                <div className="metric-label">Negative Feedbacks</div>
                            </div>
                        </div>
                        <div className="metric-card">
                            <div className="metric-icon" style={{ backgroundColor: '#8b5cf615' }}>
                                <TrendingUp size={24} color="#8b5cf6" />
                            </div>
                            <div className="metric-content">
                                <div className="metric-value">{metrics.detectedThemes}</div>
                                <div className="metric-label">Detected Themes</div>
                            </div>
                        </div>
                    </div>

                    {/* --- Content Grid --- */}
                    <div className="content-grid">

                        {/* Theme Analysis Card */}
                        <div className="card theme-analysis-card">
                            <div className="card-header">
                                <h3 className="card-title">Theme Analysis</h3>
                                <div className="header-badges">
                                    <span className="ai-badge">AI-Detected</span>
                                </div>
                            </div>
                            <p className="card-subtitle">
                                Top themes based on volume and sentiment impact
                                <span style={{ fontWeight: 'bold' }}>{periodLabel && ` ${periodLabel}`}</span>
                            </p>

                            {themes.length === 0 ? (
                                <p className="no-data">No themes found matching these filters.</p>
                            ) : (
                                <div className="themes-list">
                                    {themes.map(theme => (
                                        <div key={theme.id} className="theme-item">
                                            <div className="theme-icon" style={{ backgroundColor: `${theme.color}15` }}>
                                                {theme.icon}
                                            </div>
                                            <div className="theme-content">
                                                <div className="theme-header">
                                                    <span className="theme-title">{theme.title}</span>
                                                    <div className="theme-meta">
                                                        <span className="theme-mentions">{theme.mentions} comments</span>

                                                        {/* Smart Trend Indicator */}
                                                        {theme.trendValue !== "No Change" && (
                                                            <span className="theme-trend" style={{
                                                                color: theme.trendDirection === 'up' ? '#10b981' :
                                                                    theme.trendDirection === 'down' ? '#ef4444' : '#6b7280',
                                                                backgroundColor: theme.trendDirection === 'up' ? '#ecfdf5' : '#fef2f2',
                                                                padding: '2px 6px',
                                                                borderRadius: '4px',
                                                                fontSize: '0.85rem',
                                                                fontWeight: '600'
                                                            }}>
                                                                {theme.trendDirection === 'up' ? '▲' : '▼'} {theme.trendValue}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="progress-bar">
                                                    <div className="progress-fill" style={{ width: `${theme.impact}%`, backgroundColor: theme.color }}></div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Recent Comments Card */}
                        <div className="card feedback-samples-card">
                            <div className="card-header">
                                <h3 className="card-title">Recent Comments</h3>
                            </div>
                            <p className="card-subtitle">Latest feedback based on selection</p>

                            {recentFeedback.length === 0 ? (
                                <p className="no-data">No recent feedback found.</p>
                            ) : (
                                <div className="feedback-list">
                                    {recentFeedback.map((feedback, idx) => (
                                        <div key={idx} className="feedback-item">
                                            <div className="feedback-quote">"{feedback.comment}"</div>
                                            <div className="feedback-tags">
                                                <span className={`tag tag-${(feedback.sentiment || 'neutral').toLowerCase() === 'negative' ? 'negative' : 'positive'}`}>
                                                    {feedback.category}
                                                </span>
                                                <span className={`tag tag-sentiment-${(feedback.sentiment || 'neutral').toLowerCase()}`}>
                                                    {feedback.sentiment}
                                                </span>
                                                <span className="feedback-date">
                                                    {feedback.submission_date}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default Feedback;