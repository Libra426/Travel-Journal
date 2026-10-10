// ===== 地图功能 =====
const chinaMapObj = document.getElementById('chinaMap');
const mapTooltip = document.getElementById('mapTooltip');
let visitedProvinces = new Map(); // 存储省份名称和访问日期
let visitedCities = new Map(); // 存储城市名称和访问日期

// 城市坐标（对应 china-map.svg 的 viewBox 0 0 600 500）
const CITY_COORDS = {
    '北京': [410, 182], '上海': [490, 291], '天津': [432, 200], '重庆': [325, 320],
    '西安': [330, 278], '延安': [335, 258], '咸阳': [325, 282],
    '广州': [398, 405], '深圳': [410, 415], '珠海': [402, 418], '佛山': [395, 408],
    '杭州': [465, 318], '宁波': [478, 322], '温州': [472, 338],
    '南京': [447, 282], '苏州': [465, 290], '无锡': [458, 288],
    '济南': [425, 245], '青岛': [452, 245], '烟台': [462, 232],
    '石家庄': [392, 222], '唐山': [412, 205],
    '郑州': [388, 276], '洛阳': [375, 272],
    '武汉': [392, 310], '宜昌': [368, 314],
    '长沙': [378, 352], '岳阳': [385, 342],
    '成都': [268, 325], '绵阳': [272, 312],
    '昆明': [265, 398], '大理': [245, 390], '丽江': [240, 382],
    '沈阳': [472, 158], '大连': [465, 182],
    '长春': [488, 132],
    '哈尔滨': [488, 84],
    '合肥': [432, 302],
    '福州': [448, 368], '厦门': [442, 380],
    '南昌': [420, 348],
    '太原': [368, 232],
    '兰州': [278, 262],
    '西宁': [208, 250],
    '呼和浩特': [360, 162],
    '南宁': [340, 408],
    '贵阳': [318, 370],
    '银川': [300, 230],
    '乌鲁木齐': [100, 172],
    '拉萨': [115, 310],
    '台北': [487, 382],
    '香港': [428, 415],
    '澳门': [405, 432],
    '海口': [355, 455], '三亚': [358, 472]
};

// 清空已访问省份
function clearVisitedProvinces() {
    visitedProvinces.clear();
    visitedCities.clear();
    updateVisitedProvinces();
    renderCityMarkers();
}

const provinceMap = {
    '北京': '北京', '上海': '上海', '广东': '广东', '浙江': '浙江', '江苏': '江苏',
    '山东': '山东', '河北': '河北', '河南': '河南', '湖北': '湖北', '湖南': '湖南',
    '四川': '四川', '云南': '云南', '辽宁': '辽宁', '吉林': '吉林', '黑龙江': '黑龙江',
    '安徽': '安徽', '福建': '福建', '江西': '江西', '山西': '山西', '陕西': '陕西',
    '甘肃': '甘肃', '青海': '青海', '内蒙古': '内蒙古', '广西': '广西', '贵州': '贵州',
    '宁夏': '宁夏', '新疆': '新疆', '西藏': '西藏', '台湾': '台湾', '香港': '香港', '澳门': '澳门',
    '天津': '天津', '重庆': '重庆', '海南': '海南'
};

function getSvgDoc() {
    return chinaMapObj && chinaMapObj.contentDocument;
}

function getCityLayer() {
    const svgDoc = getSvgDoc();
    if (!svgDoc) return null;
    let layer = svgDoc.getElementById('city-layer');
    if (!layer) {
        layer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        layer.setAttribute('id', 'city-layer');
        const svgRoot = svgDoc.querySelector('svg');
        if (svgRoot) {
            svgRoot.appendChild(layer);
        }
    }
    return layer;
}

function renderCityMarkers() {
    const layer = getCityLayer();
    if (!layer) return;
    layer.innerHTML = '';

    visitedCities.forEach((visitDate, city) => {
        const coords = CITY_COORDS[city];
        if (!coords) return;

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords[0]);
        circle.setAttribute('cy', coords[1]);
        circle.setAttribute('r', '3.5');
        circle.setAttribute('fill', '#C89588');
        circle.setAttribute('stroke', '#FFFEFA');
        circle.setAttribute('stroke-width', '1');
        circle.setAttribute('style', 'cursor: pointer;');

        const tipText = `${city}\n访问时间: ${visitDate}`;
        circle.addEventListener('mouseover', function (e) {
            showTooltipRaw(e.clientX, e.clientY, tipText);
        });
        circle.addEventListener('mousemove', function (e) {
            showTooltipRaw(e.clientX, e.clientY, tipText);
        });
        circle.addEventListener('mouseout', function () {
            hideTooltip();
        });

        layer.appendChild(circle);
    });
}

function initMap() {
    if (!chinaMapObj) return;

    // 等待SVG加载完成
    chinaMapObj.addEventListener('load', function () {
        const svgDoc = chinaMapObj.contentDocument;
        if (!svgDoc) return;

        const provinces = svgDoc.querySelectorAll('.province');

        provinces.forEach(province => {
            // 获取省份名称：查找相邻的文本元素
            let provinceName = '';
            const nextElement = province.nextElementSibling;
            if (nextElement && nextElement.classList.contains('province-text')) {
                provinceName = nextElement.textContent.trim();
            }

            province.addEventListener('mouseover', function (e) {
                const x = e.clientX;
                const y = e.clientY;
                showTooltip(x, y, provinceName);
            });

            province.addEventListener('mouseout', function () {
                hideTooltip();
            });

            province.addEventListener('mousemove', function (e) {
                const x = e.clientX;
                const y = e.clientY;
                showTooltip(x, y, provinceName);
            });
        });

        // 初始化已访问省份和城市
        updateVisitedProvinces();
        renderCityMarkers();
    });
}

function showTooltipRaw(x, y, text) {
    if (!mapTooltip) return;
    mapTooltip.textContent = text;
    mapTooltip.style.left = (x + 10) + 'px';
    mapTooltip.style.top = (y + 10) + 'px';
    mapTooltip.classList.add('show');
}

function showTooltip(x, y, provinceName) {
    let text = provinceName;
    // 如果是已访问的省份，显示访问日期
    if (visitedProvinces.has(provinceName)) {
        const visitDate = visitedProvinces.get(provinceName);
        text += `\n访问时间: ${visitDate}`;
    }
    showTooltipRaw(x, y, text);
}

function hideTooltip() {
    if (!mapTooltip) return;
    mapTooltip.classList.remove('show');
}

function markProvinceVisited(provinceName, visitDate) {
    if (provinceMap[provinceName]) {
        visitedProvinces.set(provinceName, visitDate);
        updateVisitedProvinces();
    }
}

function markCityVisited(cityName, visitDate) {
    if (CITY_COORDS[cityName]) {
        visitedCities.set(cityName, visitDate);
        renderCityMarkers();
    }
}

function updateVisitedProvinces() {
    if (!chinaMapObj || !chinaMapObj.contentDocument) return;

    const svgDoc = chinaMapObj.contentDocument;
    const provinces = svgDoc.querySelectorAll('.province');
    provinces.forEach(province => {
        // 获取省份名称：查找相邻的文本元素
        let name = '';
        const nextElement = province.nextElementSibling;
        if (nextElement && nextElement.classList.contains('province-text')) {
            name = nextElement.textContent.trim();
        }

        if (visitedProvinces.has(name)) {
            province.classList.add('visited');
        } else {
            province.classList.remove('visited');
        }
    });
}

function updateMap(location, lat, lon, visitDate) {
    if (!location) return;

    console.log('Updating map with location:', location, 'visitDate:', visitDate);

    // 省份高亮
    const provinceNames = Object.keys(provinceMap);
    for (const name of provinceNames) {
        if (location.includes(name)) {
            console.log('Found province:', name);
            markProvinceVisited(name, visitDate);
            break;
        }
    }

    // 城市标记
    const cityNames = Object.keys(CITY_COORDS);
    for (const city of cityNames) {
        if (location.includes(city)) {
            console.log('Found city:', city);
            markCityVisited(city, visitDate);
            break;
        }
    }
}

// 页面加载完成后初始化地图
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMap);
} else {
    initMap();
}
