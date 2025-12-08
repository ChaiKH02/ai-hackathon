import { useState, useEffect, useRef } from 'react';
import StatCard from './StatCard';
import ENPSChart from '../Charts/ENPSChart';
import TrendChart from './TrendChart';
import { Users, Activity, Briefcase, Upload } from 'lucide-react';
import API_URL from '../../config';

const Dashboard = () => {
    const currentYear = new Date().getFullYear();
    const [selectedDept, setSelectedDept] = useState('All');
    const [selectedQuarter, setSelectedQuarter] = useState('All');
    const [selectedYear, setSelectedYear] = useState(currentYear);
    const [departmentOptions, setDepartmentOptions] = useState([]);
    const [metricsData, setMetricsData] = useState(null);
    const [trendData, setTrendData] = useState(null);
    const [loadingMetrics, setLoadingMetrics] = useState(false);

    console.log("API URL: ", process.env.REACT_APP_BACKEND_API_URL);


    const [uploadStatus, setUploadStatus] = useState(null); // null, 'processing', 'completed', 'failed'
    const [uploadMessage, setUploadMessage] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [uploadTaskId, setUploadTaskId] = useState(null);

    // Fetch Departments - same as before
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await fetch(`${API_URL}/departments`);
                const data = await response.json();

                // Helper to unmarshall DynamoDB JSON if needed
                const unmarshall = (item) => {
                    const newItem = {};
                    for (const key in item) {
                        const val = item[key];
                        if (val && typeof val === 'object') {
                            if (val.S !== undefined) newItem[key] = val.S;
                            else if (val.N !== undefined) newItem[key] = Number(val.N);
                            else newItem[key] = val; // Fallback
                        } else {
                            newItem[key] = val;
                        }
                    }
                    return newItem;
                };

                const processed = data.map(item => {
                    // Check if it looks like DynamoDB JSON (has S, N keys nested)
                    const values = Object.values(item);
                    const isDynamo = values.some(v => v && (v.S !== undefined || v.N !== undefined));
                    return isDynamo ? unmarshall(item) : item;
                });

                const deptNames = processed.map(d => d.Department_Name).filter(Boolean);
                // Deduplicate just in case
                const uniqueDepts = [...new Set(deptNames)];
                setDepartmentOptions(['All', ...uniqueDepts]);
            } catch (error) {
                console.error("Failed to fetch departments", error);
                // Fallback to mock data if API fails
                setDepartmentOptions(['All']);
            }
        };
        fetchDepartments();
    }, []);

    // Effect to update trendDept/Year when global changes initially or if we want them locked. 
    // Actually, user wants "add a year and department filter", likely implying independent control. 
    // Let's initialize them with defaults (All, currentYear) and let user change them.
    // If we want to sync them initially, we can do that, but independent is safer for "drill down".
    // However, usually if I change the global filter, I expect everything to update. 
    // Let's make them independent but maybe we can sync on mount? Default values already cover that.

    // Fetch Metrics when GLOBAL filters change
    useEffect(() => {
        const fetchMetrics = async () => {
            setLoadingMetrics(true);
            try {
                const params = new URLSearchParams();
                if (selectedDept !== 'All') params.append('departments', selectedDept);
                if (selectedQuarter !== 'All') params.append('quarter', selectedQuarter);
                params.append('year', selectedYear);

                const response = await fetch(`${API_URL}/metrics?${params.toString()}`);
                const data = await response.json();

                if (Array.isArray(data) && data.length > 0) {
                    setMetricsData(data[0]);
                } else {
                    setMetricsData(null);
                }
            } catch (error) {
                console.error("Failed to fetch metrics", error);
                setMetricsData(null);
            } finally {
                setLoadingMetrics(false);
            }
        };

        fetchMetrics();
    }, [selectedDept, selectedQuarter, selectedYear]);

    // Fetch Trends when GLOBAL filters change
    useEffect(() => {
        const fetchTrends = async () => {
            try {
                const params = new URLSearchParams();
                if (selectedDept !== 'All') params.append('departments', selectedDept);
                params.append('year', selectedYear);
                params.append('group_by', 'quarter');

                const response = await fetch(`${API_URL}/metrics?${params.toString()}`);
                const data = await response.json();

                if (Array.isArray(data)) {
                    const sorted = data.sort((a, b) => a.Quarter.localeCompare(b.Quarter));
                    setTrendData(sorted);
                } else {
                    setTrendData([]);
                }
            } catch (error) {
                console.error("Failed to fetch trends", error);
                setTrendData([]);
            }
        };
        fetchTrends();
    }, [selectedDept, selectedYear]);



    // Polling for upload status
    useEffect(() => {
        let intervalId;
        if (isUploading && uploadTaskId) {
            intervalId = setInterval(async () => {
                try {
                    const response = await fetch(`${API_URL}/upload/status/${uploadTaskId}`);
                    if (response.ok) {
                        const statusData = await response.json();
                        setUploadStatus(statusData.status);
                        setUploadMessage(statusData.message);

                        if (statusData.status === 'completed') {
                            setIsUploading(false);
                            setUploadTaskId(null);
                            alert("Processing complete! Data has been updated.");
                            window.location.reload();
                        } else if (statusData.status === 'failed') {
                            setIsUploading(false);
                            setUploadTaskId(null);
                            alert(`Processing failed: ${statusData.message}`);
                        }
                    }
                } catch (error) {
                    console.error("Error polling status:", error);
                }
            }, 2000); // Poll every 2 seconds
        }
        return () => clearInterval(intervalId);
    }, [isUploading, uploadTaskId]);

    const departments = departmentOptions.length > 0 ? departmentOptions : ['All'];
    // User requested range 1-4 (Q1-Q4)
    const quarters = ['All', 'Q1', 'Q2', 'Q3', 'Q4'];

    const years = Array.from({ length: 11 }, (_, i) => currentYear - i);

    // Use API data (metricsData) 
    const metrics = metricsData;

    const fileInputRef = useRef(null);

    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_URL}/upload/csv`, {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                const data = await response.json();
                setUploadTaskId(data.task_id);
                setIsUploading(true);
                setUploadStatus('pending');
                setUploadMessage('Upload started, processing in background...');
            } else {
                const err = await response.json();
                alert(`Upload failed: ${err.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error("Error uploading file:", error);
            alert("Error uploading file.");
        }

        // Reset file input
        event.target.value = '';
    };

    if (loadingMetrics) {
        return <div style={{ padding: '2rem' }}>Loading metrics...</div>;
    }

    if (!metrics) {
        return (
            <div style={{ padding: '2rem' }}>
                <div className="filter-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <select
                            className="filter-select"
                            value={selectedDept}
                            onChange={(e) => setSelectedDept(e.target.value)}
                        >
                            {departments.map(d => <option key={d} value={d}>{d} Department</option>)}
                        </select>
                        <select
                            className="filter-select"
                            value={selectedQuarter}
                            onChange={(e) => setSelectedQuarter(e.target.value)}
                        >
                            {quarters.map(q => <option key={q} value={q}>{q}</option>)}
                        </select>
                        <select
                            className="filter-select"
                            value={selectedYear}
                            onChange={(e) => setSelectedYear(e.target.value)}
                        >
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        {isUploading && (
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                <span style={{ fontWeight: 500 }}>{uploadStatus === 'processing' ? 'Running Analysis...' : 'Processing...'}</span>
                                <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{uploadMessage}</span>
                            </div>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            accept=".csv"
                            onChange={handleFileChange}
                            disabled={isUploading}
                        />
                        <button
                            onClick={() => fileInputRef.current.click()}
                            disabled={isUploading}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.5rem 1rem',
                                backgroundColor: isUploading ? 'var(--text-secondary)' : 'var(--primary)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: isUploading ? 'not-allowed' : 'pointer',
                                fontSize: '0.875rem'
                            }}
                        >
                            {isUploading ? (
                                <div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                            ) : (
                                <Upload size={16} />
                            )}
                            {isUploading ? 'Processing...' : 'Upload CSV'}
                        </button>
                    </div>
                </div>
                <div>No data available for this selection.</div>
            </div>
        );
    }

    return (
        <div style={{ paddingBottom: '2rem' }}>
            {/* Filters */}
            <div className="filter-bar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <select
                        className="filter-select"
                        value={selectedDept}
                        onChange={(e) => setSelectedDept(e.target.value)}
                    >
                        {departments.map(d => <option key={d} value={d}>{d === 'All' ? 'All Departments' : d}</option>)}
                    </select>
                    <select
                        className="filter-select"
                        value={selectedQuarter}
                        onChange={(e) => setSelectedQuarter(e.target.value)}
                    >
                        {quarters.map(q => <option key={q} value={q}>{q === 'All' ? 'All Quarters' : q}</option>)}
                    </select>
                    <select
                        className="filter-select"
                        value={selectedYear}
                        onChange={(e) => setSelectedYear(e.target.value)}
                    >
                        {years.map(y => <option key={y} value={y}>{y}</option>)}
                    </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    {isUploading && (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <span style={{ fontWeight: 500 }}>{uploadStatus === 'processing' ? 'Running Analysis...' : 'Processing...'}</span>
                            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{uploadMessage}</span>
                        </div>
                    )}
                    <input
                        type="file"
                        ref={fileInputRef}
                        style={{ display: 'none' }}
                        accept=".csv"
                        onChange={handleFileChange}
                        disabled={isUploading}
                    />
                    <button
                        onClick={() => fileInputRef.current.click()}
                        disabled={isUploading}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 1rem',
                            backgroundColor: isUploading ? 'var(--text-secondary)' : 'var(--primary)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: isUploading ? 'not-allowed' : 'pointer',
                            fontSize: '0.875rem'
                        }}
                    >
                        {isUploading ? (
                            <div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                        ) : (
                            <Upload size={16} />
                        )}
                        {isUploading ? 'Processing...' : 'Upload CSV'}
                    </button>
                </div>
            </div>

            {/* KPI Grid */}
            <div className="dashboard-grid">
                <StatCard
                    title="Response Rate"
                    value={metrics.Response_Rate ? `${metrics.Response_Rate.toFixed(1)}%` : 'N/A'}
                    subtext={`${metrics.Response_Count}/${metrics.Total_Employees} Responses`}
                    icon={Users}
                    color="var(--primary)"
                    trend="up"
                    trendValue="+5%"
                />
                <StatCard
                    title="Engagement Score"
                    value={metrics.Overall_Engagement ? metrics.Overall_Engagement.toFixed(2) : 'N/A'}
                    subtext="Out of 5.0"
                    icon={Activity}
                    color="var(--success)"
                    trend="up"
                    trendValue="+0.2"
                />
                <StatCard
                    title="Burnout Risk (100%)"
                    value={metrics.Burnout_Rate ? metrics.Burnout_Rate.toFixed(1) + "%" : 'N/A'}
                    subtext="Risk Level"
                    icon={Briefcase}
                    color="var(--warning)"
                    trend="neutral"
                    trendValue={metrics.Burnout_Rate >= 40 ? "High" : "Low"}
                />
                <StatCard
                    title="Turnover Risk (100%)"
                    value={metrics.Turnover_Risk ? metrics.Turnover_Risk.toFixed(1) + "%" : 'N/A'}
                    subtext="Risk Level"
                    icon={Briefcase}
                    color="var(--warning)"
                    trend="neutral"
                    trendValue={metrics.Turnover_Risk >= 40 ? "High" : "Low"}
                />
            </div>

            {/* Charts Row */}
            <div className="dashboard-grid">
                <ENPSChart
                    data={{
                        promoters: metrics.eNPS_Promoters || 0,
                        passives: metrics.eNPS_Passives || 0,
                        detractors: metrics.eNPS_Detractors || 0
                    }}
                    score={metrics.eNPS}
                />

                {/* Placeholder for Data Table or Dimensions */}
                <div className="card span-2">
                    <h3 className="card-title">Key Drivers</h3>
                    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <SkillBar label="Job Satisfaction" value={metrics.Job_Satisfaction} color="var(--primary)" />
                        <SkillBar label="Work Life Balance" value={metrics.Work_Life_Balance} color="var(--secondary)" />
                        <SkillBar label="Manager Support" value={metrics.Manager_Support} color="var(--accent)" />
                        <SkillBar label="Growth Opportunities" value={metrics.Growth_Opportunities} color="var(--success)" />
                    </div>
                </div>
            </div>

            {/* Trend Charts */}
            {trendData && trendData.length > 0 && (
                <div className="dashboard-grid" style={{ marginTop: '2rem' }}>
                    <TrendChart
                        data={trendData}
                        title={`Key Metrics Trends - ${selectedDept === 'All' ? 'All Departments' : selectedDept} (${selectedYear})`}
                        lines={[
                            { key: "Burnout_Rate", name: "Burnout Risk (%)", color: "#ef4444" },
                            { key: "Turnover_Risk", name: "Turnover Risk (%)", color: "#f59e0b" },
                            { key: "Overall_Engagement", name: "Engagement Score", color: "#10b981" },
                            { key: "eNPS", name: "eNPS", color: "#3b82f6" }
                        ]}
                    />
                </div>
            )}
        </div>
    );
};

// Simple internal sub-component
const SkillBar = ({ label, value, color }) => (
    <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem', fontSize: '0.875rem' }}>
            <span>{label}</span>
            <span style={{ fontWeight: 600 }}>{value ? value.toFixed(1) : '0.0'} / 5</span>
        </div>
        <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-light)', borderRadius: '4px' }}>
            <div style={{
                width: `${(value / 5) * 100}%`,
                height: '100%',
                backgroundColor: color,
                borderRadius: '4px'
            }}></div>
        </div>
    </div>
);

export default Dashboard;
