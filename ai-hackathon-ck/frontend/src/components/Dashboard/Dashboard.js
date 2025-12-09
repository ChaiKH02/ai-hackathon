import { useState, useEffect, useRef } from 'react';
import StatCard from './StatCard';
import TrendChart from './TrendChart';
import SeasonInsights from './SeasonInsights';
import { Users, Briefcase, Upload, RefreshCw, UserX, TrendingUp, Filter } from 'lucide-react';
import API_URL from '../../config';

const Dashboard = () => {
    const currentYear = new Date().getFullYear();
    const [selectedDept, setSelectedDept] = useState('All');
    const [selectedQuarter, setSelectedQuarter] = useState('All');
    const [selectedYear, setSelectedYear] = useState(currentYear);
    const [departmentOptions, setDepartmentOptions] = useState([]);
    const [metricsData, setMetricsData] = useState(null);
    const [trendData, setTrendData] = useState(null);
    const [seasonData, setSeasonData] = useState(null);
    const [loadingMetrics, setLoadingMetrics] = useState(false);
    const [loadingSeason, setLoadingSeason] = useState(false);

    const [uploadStatus, setUploadStatus] = useState(null);
    const [uploadMessage, setUploadMessage] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const [uploadTaskId, setUploadTaskId] = useState(null);

    // Fetch Departments
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await fetch(`${API_URL}/departments`);
                const data = await response.json();

                const unmarshall = (item) => {
                    const newItem = {};
                    for (const key in item) {
                        const val = item[key];
                        if (val && typeof val === 'object') {
                            if (val.S !== undefined) newItem[key] = val.S;
                            else if (val.N !== undefined) newItem[key] = Number(val.N);
                            else newItem[key] = val;
                        } else {
                            newItem[key] = val;
                        }
                    }
                    return newItem;
                };

                const processed = data.map(item => {
                    const values = Object.values(item);
                    const isDynamo = values.some(v => v && (v.S !== undefined || v.N !== undefined));
                    return isDynamo ? unmarshall(item) : item;
                });

                const deptNames = processed.map(d => d.Department_Name).filter(Boolean);
                const uniqueDepts = [...new Set(deptNames)];
                setDepartmentOptions(['All', ...uniqueDepts]);
            } catch (error) {
                console.error("Failed to fetch departments", error);
                setDepartmentOptions(['All']);
            }
        };
        fetchDepartments();
    }, []);

    // Fetch Metrics
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
        const fetchSeasonData = async () => {
            setLoadingSeason(true);
            try {
                const params = new URLSearchParams();
                // Match the query params to your API requirements
                if (selectedDept !== 'All') params.append('department', selectedDept);
                if (selectedQuarter !== 'All') params.append('quarter', selectedQuarter);
                if (selectedYear !== 'All') params.append('year', selectedYear);

                const response = await fetch(`${API_URL}/season/top-events?${params.toString()}`);
                const data = await response.json();
                setSeasonData(data); // Store the full JSON object
            } catch (error) {
                console.error("Failed to fetch season data", error);
                setSeasonData(null);
            } finally {
                setLoadingSeason(false);
            }
        };


        fetchMetrics();
        fetchSeasonData();
    }, [selectedDept, selectedQuarter, selectedYear]);

    // Fetch Trends
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
            }, 2000);
        }
        return () => clearInterval(intervalId);
    }, [isUploading, uploadTaskId]);

    const departments = departmentOptions.length > 0 ? departmentOptions : ['All'];
    const quarters = ['All', 'Q1', 'Q2', 'Q3', 'Q4'];
    const years = Array.from({ length: 11 }, (_, i) => currentYear - i);
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
                        <select className="filter-select" value={selectedDept} onChange={(e) => setSelectedDept(e.target.value)}>
                            {departments.map(d => <option key={d} value={d}>{d} Department</option>)}
                        </select>
                        <select className="filter-select" value={selectedQuarter} onChange={(e) => setSelectedQuarter(e.target.value)}>
                            {quarters.map(q => <option key={q} value={q}>{q}</option>)}
                        </select>
                        <select className="filter-select" value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)}>
                            {years.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                    </div>
                    <button onClick={() => fileInputRef.current.click()} disabled={isUploading}>
                        {isUploading ? 'Processing...' : 'Upload CSV'}
                    </button>
                </div>
                <div>No data available for this selection.</div>
            </div>
        );
    }

    return (
        <div style={{ paddingBottom: '2rem' }}>
            {/* Filters */}
            <div className="filter-bar-modern">
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <Filter size={20} color="var(--text-secondary)" />
                    <span style={{ fontSize: '0.875rem', fontWeight: '500', color: 'var(--text-secondary)', marginRight: '0.5rem' }}>Filters:</span>
                    <select className="filter-select-modern" value={selectedDept} onChange={(e) => setSelectedDept(e.target.value)}>
                        {departments.map(d => <option key={d} value={d}>{d === 'All' ? 'All Departments' : d}</option>)}
                    </select>
                    <select className="filter-select-modern" value={selectedQuarter} onChange={(e) => setSelectedQuarter(e.target.value)}>
                        {quarters.map(q => <option key={q} value={q}>{q === 'All' ? 'All Quarters' : q}</option>)}
                    </select>
                    <select className="filter-select-modern" value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)}>
                        <option value="All">All Years</option>
                        {years.map(y => <option key={y} value={y}>{y}</option>)}
                    </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    {isUploading && (
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <span style={{ fontWeight: 500 }}>{uploadStatus === 'processing' ? 'Running Analysis...' : 'Processing...'}</span>
                            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{uploadMessage}</span>
                        </div>
                    )}
                    <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".csv" onChange={handleFileChange} disabled={isUploading} />
                    <button onClick={() => fileInputRef.current.click()} disabled={isUploading} className="upload-btn">
                        {isUploading ? <div className="spinner"></div> : <Upload size={16} />}
                        {isUploading ? 'Processing...' : 'Upload CSV'}
                    </button>
                    <button onClick={() => window.location.reload()} className="refresh-btn">
                        <RefreshCw size={16} />
                        Refresh Data
                    </button>
                </div>
            </div>

            {/* KPI Grid - 4 Key Metrics */}
            <div className="stats-grid-4">
                <StatCard
                    title="Response Rate"
                    value={metrics.Response_Rate != null ? `${metrics.Response_Rate.toFixed(1)}%` : 'N/A'}
                    subtext={`${metrics.Response_Count || 0}/${metrics.Total_Employees || 0} Survey Responses`}
                    icon={Users}
                    color="#3b82f6"
                    trend="neutral"
                    trendValue=""
                />
                <StatCard
                    title="Burnout Rate"
                    value={metrics.Burnout_Rate != null ? `${metrics.Burnout_Rate.toFixed(1)}%` : 'N/A'}
                    subtext="Employees at Risk"
                    icon={Briefcase}
                    color="#f59e0b"
                    trend="neutral"
                    trendValue=""
                />
                <StatCard
                    title="Turnover Risk"
                    value={metrics.Turnover_Risk != null ? `${metrics.Turnover_Risk.toFixed(1)}%` : 'N/A'}
                    subtext="Attrition Risk Level"
                    icon={UserX}
                    color="#ef4444"
                    trend="neutral"
                    trendValue=""
                />
                <StatCard
                    title="Engagement Score"
                    value={metrics.Overall_Engagement != null ? `${(metrics.Overall_Engagement * 20).toFixed(1)}%` : 'N/A'}
                    subtext="Overall Employee Engagement"
                    icon={TrendingUp}
                    color="#10b981"
                    trend="neutral"
                    trendValue=""
                />
            </div>

            {/* Charts Row */}
            <div className="charts-row">
                {/* Engagement Trends Chart */}
                <div className="card chart-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-primary)' }}>Engagement Trends</h3>
                    </div>
                    {trendData && trendData.length > 0 ? (
                        <TrendChart
                            data={trendData}
                            title=""
                            lines={[
                                { key: "Overall_Engagement", name: "Engagement Score", color: "#10b981" },
                                { key: "Burnout_Rate", name: "Burnout Risk", color: "#f59e0b" },
                                { key: "Turnover_Risk", name: "Attrition Risk", color: "#ef4444" }
                            ]}
                        />
                    ) : (
                        <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                            No trend data available
                        </div>
                    )}
                </div>

                {/* eNPS Pie Chart */}
                <div className="card theme-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-primary)' }}>eNPS Breakdown</h3>
                        <span style={{
                            fontSize: '0.75rem',
                            color: 'white',
                            backgroundColor: '#3b82f6',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '12px',
                            fontWeight: '500'
                        }}>
                            Score: {metrics.eNPS != null ? metrics.eNPS.toFixed(2) : 'N/A'}
                        </span>
                    </div>
                    <ENPSPieChart
                        promoters={metrics.eNPS_Promoters || 0}
                        passives={metrics.eNPS_Passives || 0}
                        detractors={metrics.eNPS_Detractors || 0}
                    />
                </div>
            </div>
            {loadingSeason ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading seasonal data...</div>
            ) : (
                <SeasonInsights data={seasonData} />
            )}
        </div>
    );
};

// eNPS Pie Chart Component
const ENPSPieChart = ({ promoters, passives, detractors }) => {
    const total = promoters + passives + detractors;

    if (total === 0) {
        return (
            <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                No eNPS data available
            </div>
        );
    }

    const promotersPercent = ((promoters / total) * 100).toFixed(1);
    const passivesPercent = ((passives / total) * 100).toFixed(1);
    const detractorsPercent = ((detractors / total) * 100).toFixed(1);

    const pieStyle = {
        width: '200px',
        height: '200px',
        borderRadius: '50%',
        background: `conic-gradient(
            #10b981 0% ${promotersPercent}%,
            #fbbf24 ${promotersPercent}% ${parseFloat(promotersPercent) + parseFloat(passivesPercent)}%,
            #ef4444 ${parseFloat(promotersPercent) + parseFloat(passivesPercent)}% 100%
        )`,
        margin: '2rem auto',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
    };

    return (
        <div>
            <div style={pieStyle}></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
                <ENPSLegendItem color="#10b981" label="Promoters (9-10)" count={promoters} percent={promotersPercent} />
                <ENPSLegendItem color="#fbbf24" label="Passives (7-8)" count={passives} percent={passivesPercent} />
                <ENPSLegendItem color="#ef4444" label="Detractors (0-6)" count={detractors} percent={detractorsPercent} />
            </div>
        </div>
    );
};

// eNPS Legend Item
const ENPSLegendItem = ({ color, label, count, percent }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ width: '16px', height: '16px', backgroundColor: color, borderRadius: '4px' }}></div>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>{label}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--text-primary)' }}>{count}</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>({percent}%)</span>
        </div>
    </div>
);

export default Dashboard;
