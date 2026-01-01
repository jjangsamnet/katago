# KataGo REST API 서버

바둑 AI(KataGo) REST API 서버입니다. Render.com에 무료로 배포할 수 있습니다.

## 🚀 빠른 시작 (Render.com 배포)

### 1단계: GitHub 저장소 생성

1. GitHub에서 새 저장소 생성
2. 이 폴더의 모든 파일 업로드

### 2단계: Render.com 가입 및 연결

1. [Render.com](https://render.com) 가입 (무료)
2. **New** → **Web Service** 클릭
3. GitHub 저장소 연결

### 3단계: 배포 설정

| 항목 | 값 |
|------|-----|
| Name | `katago-server` (원하는 이름) |
| Environment | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |

### 4단계: 배포 완료

배포 후 URL이 생성됩니다:
```
https://katago-server-xxxx.onrender.com
```

## 📡 API 사용법

### 착수 요청

```bash
curl -X POST https://your-server.onrender.com/select-move \
  -H "Content-Type: application/json" \
  -d '{
    "board_size": 19,
    "moves": ["D4", "Q16", "D16"],
    "komi": 6.5
  }'
```

### 응답 예시

```json
{
  "success": true,
  "move": "Q4",
  "winrate": 52.3,
  "score": 1.5
}
```

### 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | 서버 상태 |
| `/health` | GET | 헬스체크 |
| `/select-move` | POST | AI 착수 선택 |
| `/simple-move` | POST | 간단한 AI (KataGo 없이) |
| `/analyze` | POST | 국면 분석 |

## ⚠️ 주의사항

### Render.com 무료 플랜 제한

- **CPU 전용**: GPU 없음 (느림)
- **메모리**: 512MB
- **슬립 모드**: 15분 비활동 시 슬립 → 첫 요청 느림

### KataGo 바이너리

무료 플랜에서는 KataGo 바이너리 설치가 어렵습니다.
현재는 **Simple AI 모드**로 동작합니다.

완전한 KataGo를 원한다면:
1. Render.com 유료 플랜 사용
2. 또는 AWS/GCP에 직접 배포

## 📁 파일 구조

```
katago-server/
├── app.py              # Flask 서버
├── requirements.txt    # Python 의존성
├── render.yaml         # Render.com 설정
├── config.cfg          # KataGo 설정
└── README.md           # 이 파일
```

## 🎮 바둑 앱과 연동

배포 후 바둑 앱의 서버 주소를 변경:

```javascript
const KATAGO_SERVER = 'https://your-server.onrender.com';
```

## 📝 라이선스

MIT License

---

Made with ❤️ for 바둑 교육
