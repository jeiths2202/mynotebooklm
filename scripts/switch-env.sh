#!/bin/bash
# Environment Switching Script
# Usage: ./scripts/switch-env.sh [dev|prod]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

case "$1" in
    dev|development)
        cp "$BACKEND_DIR/.env.development" "$BACKEND_DIR/.env"
        echo "✅ Switched to DEVELOPMENT environment"
        echo ""
        echo "Configuration:"
        echo "  - LLM API: http://localhost:8001 (Mock)"
        echo "  - Embedding API: http://localhost:8001 (Mock)"
        echo ""
        echo "To start:"
        echo "  1. Start mock server: cd backend && python -m uvicorn mock_server.main:app --port 8001 --reload"
        echo "  2. Start backend:     cd backend && python -m uvicorn app.main:app --port 8000 --reload"
        echo "  3. Start frontend:    cd frontend && npm run dev"
        ;;
    prod|production)
        cp "$BACKEND_DIR/.env.production" "$BACKEND_DIR/.env"
        echo "✅ Switched to PRODUCTION environment"
        echo ""
        echo "Configuration:"
        echo "  - LLM API: http://192.168.8.11:12800 (GPU Server)"
        echo "  - Embedding API: http://192.168.8.11:12800 (GPU Server)"
        echo ""
        echo "To start:"
        echo "  1. Start backend:  cd backend && python -m uvicorn app.main:app --port 8000 --reload"
        echo "  2. Start frontend: cd frontend && npm run dev"
        ;;
    status)
        if [ -f "$BACKEND_DIR/.env" ]; then
            ENV=$(grep "^ENVIRONMENT=" "$BACKEND_DIR/.env" | cut -d'=' -f2)
            MOCK=$(grep "^USE_MOCK_SERVICES=" "$BACKEND_DIR/.env" | cut -d'=' -f2)
            echo "Current environment: $ENV"
            echo "Using mock services: $MOCK"
        else
            echo "No .env file found. Run './scripts/switch-env.sh dev' or './scripts/switch-env.sh prod' first."
        fi
        ;;
    *)
        echo "Usage: $0 [dev|prod|status]"
        echo ""
        echo "Commands:"
        echo "  dev, development  - Switch to development mode (uses mock services)"
        echo "  prod, production  - Switch to production mode (uses GPU server)"
        echo "  status            - Show current environment"
        echo ""
        echo "Examples:"
        echo "  $0 dev     # Use mock services for testing"
        echo "  $0 prod    # Use real GPU server"
        echo "  $0 status  # Check current environment"
        exit 1
        ;;
esac
