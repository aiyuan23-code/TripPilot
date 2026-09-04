# TripPilot Frontend

## 本地启动

```bash
cp .env.example .env
npm install
npm run dev
```

前端地址：`http://localhost:5173`

启动前请确保 FastAPI 正在 `http://127.0.0.1:8000` 运行。

地图需要在高德控制台创建“Web端（JS API）”Key，并在 `.env` 中配置：

```text
VITE_AMAP_JS_KEY=...
VITE_AMAP_SECURITY_CODE=...
```

后端 `.env` 中的 `AMAP_MAPS_API_KEY` 是 Web Service Key，不能直接代替前端 JS API Key。

## 生产构建

生产环境建议通过服务端代理保护高德安全密钥：

```bash
cp .env.production.example .env.production
npm ci
npm run build
```

`VITE_AMAP_SERVICE_HOST=/_AMapService` 会让浏览器通过同域 Nginx
代理访问高德服务，避免把 `VITE_AMAP_SECURITY_CODE` 编译到前端产物中。
