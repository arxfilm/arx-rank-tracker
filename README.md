# ARX 네이버쇼핑 순위 추적기

네이버 검색 오픈API(쇼핑)로 매일 자동으로 순위를 조회하고, 크롬에서 바로 열어보는
대시보드(`index.html`)를 자동으로 갱신하는 도구입니다. GitHub Actions가 하루 한 번
정해진 시간에 대신 실행해주기 때문에, 컴퓨터를 켜두지 않아도 됩니다.

## 처음 한 번만 하는 설정 (5~10분)

### 1. GitHub 저장소 만들기
1. https://github.com 에서 로그인 (계정 없으면 회원가입)
2. 오른쪽 위 `+` → `New repository`
3. Repository name: `arx-rank-tracker` (원하는 이름으로 바꿔도 됩니다)
4. `Public`으로 설정 (Public이어야 GitHub Pages를 무료로 쓸 수 있어요. 코드에 API 키를
   직접 넣지 않으므로 Public이어도 안전합니다)
5. `Create repository` 클릭

### 2. 이 파일들 업로드
1. 방금 만든 저장소 페이지에서 `Add file` → `Upload files`
2. 압축을 푼 이 폴더 안의 모든 파일/폴더(`.github` 폴더 포함)를 통째로 끌어다 놓기
   - `.github` 폴더가 안 보일 수 있는데, 압축 해제한 폴더 안에 숨김 폴더로 들어있습니다.
     드래그가 안 되면 GitHub Desktop이나 `git` 명령으로 올리셔도 됩니다.
3. `Commit changes` 클릭

### 3. API 키 등록 (비밀키라서 코드에 안 넣고 여기에 따로 저장)
1. 저장소 페이지 → `Settings` → 왼쪽 메뉴 `Secrets and variables` → `Actions`
2. `New repository secret` 클릭
   - Name: `NAVER_CLIENT_ID` / Secret: (네이버 개발자센터 Client ID)
3. 한 번 더 `New repository secret`
   - Name: `NAVER_CLIENT_SECRET` / Secret: (네이버 개발자센터 Client Secret)

### 4. GitHub Pages 켜기 (대시보드를 웹주소로 보기 위함)
1. `Settings` → 왼쪽 메뉴 `Pages`
2. `Build and deployment` → `Source`: `Deploy from a branch`
3. `Branch`: `main` / 폴더: `/ (root)` 선택 → `Save`
4. 몇 분 후 페이지 상단에 뜨는 주소(`https://<계정명>.github.io/arx-rank-tracker/`)가
   대시보드 주소입니다. 이 주소를 크롬 북마크에 등록해두세요.

### 5. 첫 실행 (수동으로 1회 테스트)
1. 저장소 상단 `Actions` 탭 클릭
2. 왼쪽에서 `ARX Rank Tracker` 워크플로 선택
3. `Run workflow` → `Run workflow` 버튼 클릭
4. 1~2분 후 초록 체크가 뜨면 성공. 실패(빨간 X)하면 로그를 열어서 오류 메시지 확인
   (대부분 API 키 오타이거나, Secrets 이름이 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`과
   정확히 일치하지 않는 경우입니다)
5. 성공하면 `data/history.json`과 `index.html`이 자동으로 갱신되어 커밋됩니다.
   위 4번 주소로 접속해서 확인하세요.

## 이후엔 아무것도 안 해도 됩니다
매일 한국시간 오전 9시(UTC 00:00)에 GitHub 서버가 자동으로 실행합니다.
갱신 시각을 바꾸고 싶으면 `.github/workflows/track.yml`의 `cron: '0 0 * * *'`
부분을 수정하세요 (cron은 UTC 기준입니다).

## 키워드/상품 추가하는 법
`keywords.json`을 열어서 `products` 배열에 항목을 추가하면 됩니다. 예를 들어
베르데(증착) 상품이 등록되면 아래처럼 하나 더 추가하세요.

```json
{
  "id": "verde",
  "label": "증착 (베르데)",
  "product_id": "여기에 네이버쇼핑 상품ID(nvMid)",
  "product_title": "ARX 자동차 썬팅 필름 베르데 국산 수입차 반사 증착 열차단 미러틴팅 시공권",
  "product_url": "https://smartstore.naver.com/vision03/products/여기에 스토어 상품번호",
  "keywords": ["반사 썬팅", "증착 필름", "수입차 썬팅", "열차단 필름", "자동차 썬팅", "썬팅 재시공", "테슬라 썬팅"]
}
```

수정 후 저장소에 커밋(업로드)하면 다음 자동 실행부터 바로 반영됩니다.

## 알아둘 점
- 순위는 네이버 검색 오픈API 기준 근사치입니다. 실제 소비자가 보는 화면과 완전히
  똑같다는 보장은 없지만, 매일 같은 방식으로 재기 때문에 오르내리는 **추이**는
  신뢰할 수 있습니다.
- 최대 1000위까지만 조회됩니다. "1000위 밖"으로 뜨면 그 범위 안에서 상품을
  찾지 못했다는 뜻이며, 판매·리뷰가 쌓여 순위가 오르면 자연히 잡히기 시작합니다.
- 하루 API 호출 한도는 25,000회로, 지금 규모(상품 1개 × 키워드 9개)에서는
  하루에 최대 90회 정도만 씁니다. 여유가 매우 큽니다.
