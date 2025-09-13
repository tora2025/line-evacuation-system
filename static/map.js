// static/map.js

// 地図初期化
const map = L.map('map').setView([35.6895, 139.6917], 13); // 初期位置: 東京

// タイルレイヤ（地図背景）
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// 被害データ取得
fetch('/data')
  .then(response => response.json())
  .then(data => {
    L.geoJSON(data, {
      onEachFeature: function (feature, layer) {
        const p = feature.properties;

        // rescue_needed を人が読みやすい文字に変換
        let rescueText = "不明";
        if (p.rescue_needed === true) rescueText = "はい";
        else if (p.rescue_needed === false) rescueText = "いいえ";

        const popupHtml = `
          <div style="min-width:200px">
            <b>災害種別:</b> ${p.damage || "不明"}<br>
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
