// static/map.js

// ==========================
// カスタムマーカー生成関数
// ==========================
function getMarkerIcon(report) {
  let iconUrl = "/static/画像/マーカーアイコン灰.png"; // デフォルト

  switch (report.health_status) {
  case "重傷": iconUrl = "/static/images/marker-icon-red.png"; break;
  case "軽傷": iconUrl = "/static/images/marker-icon-orange.png"; break;
  case "無傷": iconUrl = "/static/images/marker-icon-green.png"; break;
}

  return L.icon({
    iconUrl: iconUrl,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34]
  });
}

// ==========================
// 地図初期化
// ==========================
const map = L.map('map').setView([35.6895, 139.6917], 13); // 東京中心

// 背景地図レイヤー
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// ==========================
// Supabaseデータ取得 → マーカー表示
// ==========================
fetch('/data')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      // 各地点マーカー設定
      pointToLayer: function (feature, latlng) {
        const p = feature.properties;
        const icon = getMarkerIcon(p);
        return L.marker(latlng, { icon: icon });
      },

      // ポップアップ設定
      onEachFeature: function (feature, layer) {
        const p = feature.properties;

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

