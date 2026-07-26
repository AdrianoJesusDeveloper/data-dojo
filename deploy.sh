#!/bin/bash

echo "🚀 Iniciando deploy do Data Driven Dojô..."

# 1. Deploy do Backend
echo "📦 Fazendo deploy do backend..."
git push origin main

# 2. Deploy do Frontend
echo "🎨 Fazendo deploy do frontend..."
cd frontend
npm run build
vercel --prod

echo "✅ Deploy concluído!"
echo "Frontend: https://seu-frontend.vercel.app"
echo "Backend: https://seu-backend.onrender.com"