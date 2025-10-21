// static/map.js

// ==========================
// カスタムマーカー生成関数
// ==========================
function getMarkerIcon(report) {
  // === 健康状態 → 色 ===
  let color = "gray";
  switch (report.health_status) {
    case "重傷": color = "red"; break;
    case "軽傷": color = "orange"; break;
    case "無傷": color = "green"; break;
  }

  // === 救助要否 → 形 ===
  let shape = (report.rescue_needed === true || report.rescue_needed === "はい") ? "▼" : "▼";

  // === 被害種別 → アイコン（中央に小さく） ===
  let symbol = "";
  switch (report.damage || report.damage_type) {
    case "火災": symbol = "🔥"; break;
    case "倒壊": symbol = "🏚️"; break;
    case "冠水": symbol = "💧"; break;
    case "通行止め": symbol = "🚫"; break;
    case "その他": symbol = "⚙️"; break;
  }

  // === HTML構成 ===
  const html = `
    <div style="
      position: relative;
      display: inline-block;
      color: ${color};
      font-size: 28px;
      transform: translate(-50%, -50%);
    ">
      ${shape}
      <span style="
        position: absolute;
        top: 4px; left: 6px;
        font-size: 14px;
      ">${symbol}</span>
    </div>
  `;

  return L.divIcon({
    className: "custom-marker",
    html: html,
    iconSize: [30, 30],
  });
}

// ==========================
// 地図初期化
// ==========================
const map = L.map('map').setView([35.6895, 139.6917], 13); // 初期位置: 東京

// タイルレイヤ（地図背景）
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// ==========================
// Supabaseデータ取得 → GeoJSON表示
// ==========================
fetch('/data')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      // 🔹 各地点ごとのマーカーの外観を指定
      pointToLayer: function (feature, latlng) {
        const p = feature.properties;
        const icon = getMarkerIcon(p); // カスタムマーカーを生成
        return L.marker(latlng, { icon: icon });
      },

      // 🔹 ポップアップの内容設定
      onEachFeature: function (feature, layer) {
        const p = feature.properties;

        // rescue_needed を日本語表記に
        let rescueText = "不明";
        if (p.rescue_needed === true || p.rescue_needed === "はい") rescueText = "はい";
        else if (p.rescue_needed === false || p.rescue_needed === "いいえ") rescueText = "いいえ";

        const popupHtml = `
          <div style="min-width:200px">
            <b>災害種別:</b> ${p.damage || p.damage_type || "不明"}<br>
            <b>健康状態:</b> ${p.health_status || "不明"}<br>
            <b>救助要否:</b> ${rescueText}<br>
            <b>人数:</b> ${p.people_count ?? "不明"}<br>
            <b>年齢層:</b> ${p.age_group || "不明"}<br>
            <b>コメント:</b> ${p.comment || "なし"}
          </div>
        `;
        layer.bindPopup(popupHtml);
      }
    }).addTo(map);
  })
  .catch(err => console.error('データ読み込みエラー:', err));

// ==========================
// 凡例（レジェンド）を追加
// ==========================
const legend = L.control({ position: 'topleft' }); // 左上に配置

legend.onAdd = function (map) {
  const div = L.DomUtil.create('div', 'info legend');
  div.innerHTML = `
    <div style="
      background: white;
      padding: 10px;
      border-radius: 8px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      font-size: 14px;
      line-height: 1.6;
    ">
      <b>凡例（マーカーの意味）</b><br>
      <span style="color:red;">●</span> 重傷<br>
      <span style="color:orange;">●</span> 軽傷<br>
      <span style="color:green;">●</span> 無傷<br>
      <hr style="margin:5px 0;">
      🔥 火災 &nbsp;&nbsp; 🏚️ 倒壊 &nbsp;&nbsp; 💧 冠水<br>
      🚫 通行止め &nbsp;&nbsp; ⚙️ その他<br>
      <hr style="margin:5px 0;">
      ●（赤・橙・緑）：健康状態<br>
      絵文字：被害種別
    </div>
  `;
  return div;
};

legend.addTo(map);




