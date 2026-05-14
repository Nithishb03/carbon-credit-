import React, { useState, useEffect } from 'react';
import axios from 'axios';
import CarbonAuditDashboard, { type CarbonAuditReport } from './CarbonAuditDashboard';

interface Block {
  number: number;
  hash: string;
  parentHash: string;
  timestamp: number;
  tx_count: number;
}

const App = () => {
  const [identity, setIdentity] = useState<{ address: string; private_key: string } | null>(null);
  const [blockHistory, setBlockHistory] = useState<Block[]>([]);
  const [networkLogs, setNetworkLogs] = useState<string[]>([]);
  const [auditReport, setAuditReport] = useState<CarbonAuditReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    queryNetworkBlocks();
    queryLatestAuditReport();
    const blockInterval = setInterval(() => queryNetworkBlocks(), 2000);
    const auditInterval = setInterval(() => queryLatestAuditReport(), 2000);
    return () => {
      clearInterval(blockInterval);
      clearInterval(auditInterval);
    };
  }, []);

  const generateAndOnboardIdentity = async () => {
    setLoading(true);
    setNetworkLogs(prev => [...prev, `[IDENTITY] Generating new public/private asymmetric keys...`]);
    try {
      const genRes = await axios.get('http://localhost:5000/identity/generate');
      const newIdentity = genRes.data;
      
      setNetworkLogs(prev => [...prev, `[ESCROW] Transferring initialization collateral and mining registration block...`]);
      
      await axios.post('http://localhost:5000/identity/onboard', {
        address: newIdentity.address,
        private_key: newIdentity.private_key
      });

      setIdentity(newIdentity);
      setNetworkLogs(prev => [...prev, `[SUCCESS] Node verified on RPoS layer. Secure transmission open.`]);
    } catch (e) {
      setNetworkLogs(prev => [...prev, `[ERROR] Onboarding transaction failed. See server logs.`]);
    }
    setLoading(false);
  };

  const downloadPrivateKey = () => {
    if (!identity) return;
    const element = document.createElement("a");
    const file = new Blob([
      `===================================================================\n` +
      `          DEPIN CARBON NETWORK SECURE PRIVATE SIGNING KEY          \n` +
      `===================================================================\n` +
      `PUBLIC NODE ADDRESS: ${identity.address}\n` +
      `PRIVATE SIGNING KEY: ${identity.private_key}\n` +
      `===================================================================\n`
    ], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `pkey_auth_${identity.address.substring(0, 8)}.conf`;
    document.body.appendChild(element);
    element.click();
    setNetworkLogs(prev => [...prev, `💾 Key configuration file downloaded locally.`]);
  };

  const queryNetworkBlocks = async () => {
    try {
      const res = await axios.get('http://localhost:5000/network/blocks');
      setBlockHistory(res.data);
    } catch (e) {}
  };

  const queryLatestAuditReport = async () => {
    try {
      const res = await axios.get('http://localhost:5000/audit/latest');
      if (res.data?.results) {
        setAuditReport(res.data);
      } else if (res.data?.status === 'rejected' || res.data?.status === 'waiting') {
        setAuditReport(null);
      }
    } catch (e) {}
  };

  const handleFileUploadStream = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!identity || !e.target.files || e.target.files.length === 0) return;
    setLoading(true);
    setAuditReport(null);
    const selectedFile = e.target.files[0];
    
    setNetworkLogs(prev => [...prev, `[INGESTION] Packing raw file data stream: ${selectedFile.name}`]);

    const formData = new FormData();
    formData.append("address", identity.address);
    formData.append("private_key", identity.private_key);
    formData.append("file", selectedFile);

    try {
      const res = await axios.post('http://localhost:5000/report/upload', formData);
      setNetworkLogs(prev => [
        ...prev,
        `[UPLOAD SUCCESS] File transmitted to decentralized network successfully.`,
        `  ├─ SHA-256 Hash Locked: ${res.data.hash}`,
        `  ├─ Blockchain Tx Receipt: ${res.data.tx_hash}`,
        `  └─ STATUS: PENDING. Report placed in global mempool awaiting Validator Consensus...`
      ]);
    } catch (error) {
      setNetworkLogs(prev => [...prev, `[ERROR] Upload transaction failed. Check contract linkage or server errors.`]);
    }
    setLoading(false);
  };

  const ui = {
    body: { backgroundColor: '#06080F', minHeight: '100vh', padding: '48px 32px', fontFamily: '"SF Mono", Menlo, Consolas, monospace', color: '#94A3B8' },
    layout: { maxWidth: '1280px', margin: '0 auto', display: 'flex', flexDirection: 'column' as const, gap: '32px' },
    navbar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #1E293B', paddingBottom: '24px' },
    brandTitle: { margin: 0, fontSize: '20px', fontWeight: 900, color: '#FFFFFF', letterSpacing: '3px' },
    brandSub: { margin: '6px 0 0 0', fontSize: '11px', color: '#475569', letterSpacing: '1px', textTransform: 'uppercase' as const },
    
    gridTwoColumn: { display: 'grid', gridTemplateColumns: '1fr', gap: '32px' },
    cardPanel: { backgroundColor: '#0D111C', border: '1px solid #1E293B', borderRadius: '12px', padding: '28px', display: 'flex', flexDirection: 'column' as const, gap: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.4)' },
    cardHeader: { margin: 0, fontSize: '11px', fontWeight: 700, color: '#00E699', letterSpacing: '1.5px', textTransform: 'uppercase' as const, borderBottom: '1px solid #1E293B', paddingBottom: '12px' },
    
    initButton: { backgroundColor: '#00E699', color: '#06080F', border: 'none', padding: '14px 24px', fontWeight: 'bold' as const, fontSize: '12px', letterSpacing: '1px', cursor: 'pointer', borderRadius: '6px', boxShadow: '0 0 15px rgba(0,230,153,0.3)' },
    exportButton: { backgroundColor: 'transparent', border: '1px solid #334155', color: '#38BDF8', padding: '8px 14px', fontSize: '11px', cursor: 'pointer', borderRadius: '4px', textAlign: 'right' as const, marginTop: '8px' },
    
    metricContainer: { display: 'flex', flexDirection: 'column' as const, gap: '2px' },
    metricLabel: { fontSize: '10px', color: '#475569', textTransform: 'uppercase' as const, fontWeight: 'bold' as const },
    metricValue: { fontSize: '24px', fontWeight: 700, color: '#FFFFFF', marginTop: '4px' },
    
    inputZone: { border: '2px dashed #334155', borderRadius: '8px', padding: '48px 24px', textAlign: 'center' as const, cursor: 'pointer', backgroundColor: '#090D16' },
    inputPrimaryText: { fontSize: '12px', color: '#38BDF8', fontWeight: 'bold' as const },
    inputSecondaryText: { display: 'block', fontSize: '10px', color: '#475569', marginTop: '8px' },
    
    explorerGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' },
    blockBox: { backgroundColor: '#090D16', border: '1px solid #1E293B', borderRadius: '8px', padding: '20px', display: 'flex', flexDirection: 'column' as const, gap: '12px' },
    blockHeaderRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1E293B', paddingBottom: '8px' },
    blockBadgeNum: { color: '#FFFFFF', fontWeight: 'bold' as const, fontSize: '12px' },
    blockBadgeTx: { backgroundColor: '#1E293B', color: '#00E699', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' as const },
    blockMetaLabel: { color: '#475569', fontSize: '10px', textTransform: 'uppercase' as const, display: 'block' },
    blockMetaVal: { color: '#94A3B8', fontSize: '10px', whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis', display: 'block', margin: '2px 0 0 0' },
    
    consoleFrame: { backgroundColor: '#05070A', border: '1px solid #1E293B', borderRadius: '8px', padding: '20px', height: '180px', overflowY: 'auto' as const, fontSize: '12px', lineHeight: '1.8' },
    consoleLine: { display: 'flex', gap: '12px', marginBottom: '6px' },
    consolePointer: { color: '#475569' }
  };

  return (
    <div style={ui.body}>
      <div style={ui.layout}>
        
        {/* UPPER REGISTRY HEAD */}
        <div style={ui.navbar}>
          <div>
            <h1 style={ui.brandTitle}>DEPIN <span style={{ color: '#00E699' }}>//</span> EMISSION_GRID_ALPHA</h1>
            <p style={ui.brandSub}>Autonomous Compliance Escrow Node Explorer</p>
          </div>
          {!identity ? (
            <button onClick={generateAndOnboardIdentity} disabled={loading} style={ui.initButton}>
              {loading ? "INITIALIZING SECURE ESCROW REGS..." : "MOUNT OPERATIONAL NODE"}
            </button>
          ) : (
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: '10px', color: '#00E699', backgroundColor: '#064E3B', padding: '4px 10px', borderRadius: '4px', fontWeight: 'bold', border: '1px solid #059669' }}>NODE_ONLINE</span>
              <p style={{ fontSize: '11px', color: '#64748B', marginTop: '12px' }}>ADDR: {identity.address}</p>
              <button onClick={downloadPrivateKey} style={ui.exportButton}>
                [↓ Export Dynamic Node Config Token (.conf)]
              </button>
            </div>
          )}
        </div>

        {identity && (
          <div style={ui.gridTwoColumn}>
            {/* RAW DATA TRANSMITTER DROPZONE */}
            <div style={ui.cardPanel}>
              <h3 style={ui.cardHeader}>// METRIC PROCESSING SYSTEM</h3>
              <p style={{ fontSize: '12px', color: '#64748B', margin: 0, lineHeight: '1.6' }}>
                Broadcast raw telemetry batches (.csv / .json). The node pipeline maps files directly to runtime arrays, derives the cryptographic hash values, and signs commitments directly to the public registry.
              </p>
              <label style={ui.inputZone}>
                <span style={ui.inputPrimaryText}>[ INGEST TELEMETRY COMPLIANCE FILE ]</span>
                <span style={ui.inputSecondaryText}>Accepts standard arrays structured inside un-previews CSV or JSON data documents</span>
                <input type="file" accept=".json,.csv" onChange={handleFileUploadStream} disabled={loading} style={{ display: 'none' }} />
              </label>
            </div>

          </div>
        )}

        <CarbonAuditDashboard report={auditReport} />

        {/* SECURE WRAPPING CHRONOLOGICAL BLOCK HISTORY EXPLORER */}
        <div style={ui.cardPanel}>
          <h3 style={ui.cardHeader}>// LIVE LEDGER METADATA TRACKER AGGREGATOR</h3>
          <div style={ui.explorerGrid}>
            {blockHistory.map((blk) => (
              <div key={blk.number} style={ui.blockBox}>
                <div style={ui.blockHeaderRow}>
                  <span style={ui.blockBadgeNum}>
                    {blk.number === 0 ? "GENESIS BLOCK" : `BLOCK # ${blk.number}`}
                  </span>
                  <span style={ui.blockBadgeTx}>
                    {blk.tx_count} {blk.tx_count === 1 ? "TX" : "TXS"}
                  </span>
                </div>
                <div style={{ marginTop: '4px' }}>
                  <span style={ui.blockMetaLabel}>CURRENT HASH:</span>
                  <span style={ui.blockMetaVal}>{blk.hash}</span>
                </div>
                <div style={{ marginTop: '4px' }}>
                  <span style={ui.blockMetaLabel}>PREVIOUS PARENT HASH:</span>
                  <span style={{ ...ui.blockMetaVal, color: '#475569' }}>{blk.parentHash}</span>
                </div>
                <div style={{ marginTop: '4px' }}>
                  <span style={ui.blockMetaLabel}>BLOCK METADATA TIME:</span>
                  <span style={{ ...ui.blockMetaVal, color: '#64748B' }}>
                    {new Date(blk.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* FEED PANEL */}
        <div style={ui.cardPanel}>
          <h3 style={ui.cardHeader}>// LIVE CONSOLE FEED</h3>
          <div style={ui.consoleFrame}>
            {networkLogs.length === 0 && <div style={{ color: '#475569' }}>Idle. Awaiting secure device authorization token mapping...</div>}
            {networkLogs.map((log, index) => (
              <div key={index} style={ui.consoleLine}>
                <span style={ui.consolePointer}>»</span>
                <span style={{ color: log.includes('SUCCESS') || log.includes('🔑') || log.includes('💾') ? '#00E699' : log.includes('ERROR') || log.includes('REJECTION') ? '#F87171' : '#10B981' }}>{log}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default App;
