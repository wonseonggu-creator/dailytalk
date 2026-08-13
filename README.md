# 원스회화 — Android

매일 10분 영어 (듀오링고 섹션 5 수준). `app/src/main/assets/wons.html`이 앱 본체.

## APK 빌드 (GitHub Actions)
1. 새 리포 생성 → 이 폴더 내용 전체 업로드 (`.github` 포함, 폴더째 드래그)
2. 업로드가 어려우면: zip만 올리고 `.github/workflows/build.yml`을 웹에서 직접 생성
3. Actions 완료 → Artifacts → **Wons-debug-apk** 다운로드 → 설치

## PC 동기화
PC에서 `python wons_server.py` (포트 8379) 실행 → 앱 설정에 `http://<PC IP>:8379`
