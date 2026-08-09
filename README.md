# DailyTalk — Android (Phase 1)

매일 10분 영어회화 앱의 WebView 래퍼. `app/src/main/assets/dailytalk.html`이 앱 본체.

## APK 빌드 (GitHub Actions — 원뷰어와 동일 방식)
1. GitHub에 새 리포 생성 → 이 폴더 내용 전체 업로드 (`.github` 폴더 포함)
2. 업로드하면 Actions가 자동 실행 (또는 Actions 탭 → Build APK → Run workflow)
3. 완료 후 해당 실행의 **Artifacts → DailyTalk-debug-apk** 다운로드
4. 압축 풀어 `app-debug.apk`를 폰으로 옮겨 설치 (출처를 알 수 없는 앱 허용)

## 앱에서 PC 동기화
나 탭 → 설정 → 동기화 서버에 `http://<PC IP>:8378` 입력
(PC에서 `python english_app_v2.py` 실행 중일 때 업로드/불러오기 동작)

## 콘텐츠 업데이트 방법
`dailytalk.html`만 새 버전으로 교체하고 push → 새 APK 자동 빌드
