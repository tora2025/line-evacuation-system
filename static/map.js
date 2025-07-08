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
  .then(geojson => {
    L.geoJSON(geojson, {
      onEachFeature: function (feature, layer) {
        const damage = feature.properties.damage || '不明';
        layer.bindPopup(`<div class="damage-popup">被害情報：${damage}</div>`);
      },
      pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, {
          radius: 8,
          fillColor: "#ff0000",
          color: "#fff",
          weight: 1,
          opacity: 1,
          fillOpacity: 0.8
        });
      }
    }).addTo(map);
  })
  .catch(error => console.error('データ取得エラー:', error));
