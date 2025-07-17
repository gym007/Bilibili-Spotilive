import React from 'react';

// Helper component for a single form field
const FormField = ({ label, value, isSecret = false }) => (
  <div className="mb-3">
    <label className="form-label fw-bold">{label}</label>
    <input
      type={isSecret ? 'password' : 'text'}
      className="form-control"
      value={value || ''}
      readOnly
    />
  </div>
);

// Helper component for permission settings
const PermissionGroup = ({ title, permissions }) => {
  if (!permissions) return null;
  return (
    <div className="card mb-4">
      <div className="card-header">{title}</div>
      <div className="card-body">
        <div className="row">
          <div className="col-md-6">
            <FormField label="所需粉丝牌等级" value={permissions.medal_level} />
          </div>
        </div>
        <div className="d-flex flex-wrap gap-4 mt-2">
          <div className="form-check form-switch">
            <input className="form-check-input" type="checkbox" checked={permissions.streamer} disabled />
            <label className="form-check-label">主播</label>
          </div>
          <div className="form-check form-switch">
            <input className="form-check-input" type="checkbox" checked={permissions.room_admin} disabled />
            <label className="form-check-label">房管</label>
          </div>
          <div className="form-check form-switch">
            <input className="form-check-input" type="checkbox" checked={permissions.guard} disabled />
            <label className="form-check-label">大航海</label>
          </div>
          <div className="form-check form-switch">
            <input className="form-check-input" type="checkbox" checked={permissions.medal_light} disabled />
            <label className="form-check-label">点亮粉丝牌</label>
          </div>
        </div>
      </div>
    </div>
  );
};

const ConfigPage = ({ config, error }) => {
  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  if (!config) {
    return <div>加载中...</div>;
  }

  return (
    <div>
      <h1 className="mb-4">应用配置</h1>
      
      <div className="config-columns-container">
        <div className="card mb-4">
          <div className="card-header fs-4">Bilibili 设置</div>
          <div className="card-body">
            <FormField label="房间号" value={config.bilibili?.room_id} />
            <hr/>
            <h5 className="mt-4">Bilibili浏览器cookies</h5>
            <FormField label="SESSDATA" value={config.bilibili?.credential?.sessdata} isSecret />
            <FormField label="Bili_JCT" value={config.bilibili?.credential?.bili_jct} isSecret />
          </div>
        </div>

        <div className="card mb-4">
          <div className="card-header fs-4">Spotify 设置</div>
          <div className="card-body">
            <FormField label="客户端 ID (Client ID)" value={config.spotify?.client_id} />
            <FormField label="客户端密钥 (Client Secret)" value={config.spotify?.client_secret} isSecret />
            <FormField label="默认歌单" value={config.spotify?.default_playlist} />
          </div>
        </div>
      </div>

      <div className="config-columns-container">
        <PermissionGroup title="点歌权限" permissions={config.bilibili?.song_request_permission} />
        <PermissionGroup title="切歌权限" permissions={config.bilibili?.next_request_permission} />
      </div>
    </div>
  );
};

export default ConfigPage;