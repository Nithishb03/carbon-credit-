export interface CarbonAuditReport {
  status?: string;
  report_hash?: string;
  updated_at?: string;
  results?: Record<string, number>;
}

interface CarbonAuditDashboardProps {
  report: CarbonAuditReport | null;
}

const metricOrder = [
  "Total Power (kWh)",
  "Allowed Emission (kg CO2)",
  "Present Emission (kg CO2)",
  "Emission Reduced (kg CO2)",
  "New Credits Earned",
  "Base Carbon Credit",
  "Updated Wallet Credits"
];

const CarbonAuditDashboard = ({ report }: CarbonAuditDashboardProps) => {
  const results = report?.results;

  const styles = {
    panel: {
      backgroundColor: '#0D111C',
      border: '1px solid #1E293B',
      borderRadius: '12px',
      padding: '28px',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '24px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
    },
    header: {
      margin: 0,
      fontSize: '11px',
      fontWeight: 700,
      color: '#00E699',
      letterSpacing: '1.5px',
      textTransform: 'uppercase' as const,
      borderBottom: '1px solid #1E293B',
      paddingBottom: '12px'
    },
    metaRow: {
      display: 'flex',
      justifyContent: 'space-between',
      gap: '16px',
      color: '#64748B',
      fontSize: '11px',
      flexWrap: 'wrap' as const
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '16px'
    },
    metricBox: {
      backgroundColor: '#090D16',
      border: '1px solid #1E293B',
      borderRadius: '8px',
      padding: '18px',
      minHeight: '92px',
      display: 'flex',
      flexDirection: 'column' as const,
      justifyContent: 'space-between'
    },
    metricBoxHighlight: {
      backgroundColor: '#06281F',
      border: '1px solid #00E699',
      boxShadow: '0 0 18px rgba(0,230,153,0.18)'
    },
    metricLabel: {
      fontSize: '10px',
      color: '#64748B',
      textTransform: 'uppercase' as const,
      fontWeight: 'bold' as const,
      lineHeight: 1.4
    },
    metricValue: {
      marginTop: '12px',
      fontSize: '24px',
      fontWeight: 800,
      color: '#FFFFFF'
    },
    highlightValue: {
      color: '#00E699',
      fontSize: '30px'
    },
    emptyState: {
      color: '#475569',
      fontSize: '12px',
      padding: '24px 0'
    }
  };

  return (
    <section style={styles.panel}>
      <h3 style={styles.header}>// CARBON CREDIT AUDIT DASHBOARD</h3>

      {!results ? (
        <div style={styles.emptyState}>Waiting for a legitimate validation report...</div>
      ) : (
        <>
          <div style={styles.metaRow}>
            <span>STATUS: {report?.status?.toUpperCase() || 'APPROVED'}</span>
            <span>UPDATED: {report?.updated_at || '--'}</span>
          </div>

          <div style={styles.grid}>
            {metricOrder.map((metric) => {
              const isCreditMetric = metric === "New Credits Earned";
              const value = metric === "Base Carbon Credit"
                ? results["Base Carbon Credit"] ?? results["Existing Wallet Credits"] ?? ((results["Allowed Emission (kg CO2)"] ?? 50000) / 1000)
                : results[metric] ?? 0;

              return (
                <div
                  key={metric}
                  style={{
                    ...styles.metricBox,
                    ...(isCreditMetric ? styles.metricBoxHighlight : {})
                  }}
                >
                  <span style={styles.metricLabel}>{metric}</span>
                  <span
                    style={{
                      ...styles.metricValue,
                      ...(isCreditMetric ? styles.highlightValue : {})
                    }}
                  >
                    {value}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
};

export default CarbonAuditDashboard;
