# FastAPI–lovable API 대응 분석

## 범위와 기준

- 백엔드: `api/main.py`의 앱과 `/api` 접두사가 붙은 `api/routes/plan.py` 라우터. FastAPI가 자동 제공하는 OpenAPI 문서 경로는 애플리케이션에서 선언한 엔드포인트가 아니므로 제외한다.
- 프론트: `lovable/` 소스의 백엔드 HTTP 호출. 공통 주소는 `lovable/src/lib/api.ts:1`의 `VITE_API_URL`이며, 미설정 시 `http://localhost:8000`이다.
- 아래의 “사용”은 `TravelPlannerApp.tsx`에서 호출 함수까지 실제 참조하는 경우를 뜻한다. 요청/응답은 코드에 선언된 형식이며 실행 결과를 검증한 것은 아니다.

## 공통 요청/응답 스키마

| 이름 | 필드 |
| --- | --- |
| `PlanRequest` | `message: str` 필수; `budget?: str`, `people?: str`, `stay?: str` (`null` 허용) |
| `ResumeRequest` | `thread_id: str`, `choice: str` 필수. 선택 번호나 숙소 선호도 JSON 문자열을 `choice`로 전달 |
| `RefineRequest` | `thread_id: str`, `feedback: str` 필수 |
| `PlaceItem` | `title: str`, `address: str`, `category: str` 필수; `description: str = ""` |
| `PlanResponse` | `intent: dict`, `weather_summary: str`, `hotel_name: str`, `hotel_address: str`, `hotel_cost: int`, `remaining_budget: int`, `restaurants: list[PlaceItem]`, `attractions: list[PlaceItem]`, `final_report: str` |
| `StartPlanResponse` | `thread_id: str`, `phase: str` 필수; `question?: str`, `candidates?: list[dict]`, `schema?: list[dict]`, `result?: PlanResponse`. `phase`는 코드상 `date_selection`, `hotel_prefs`, `hotel_selection`, `done`을 사용 |

스키마 출처: `api/schemas.py`. 프론트의 대응 타입은 `lovable/src/lib/api.ts`의 `PlanRequest`, `PlanResult`, `StartPlanResult` 등이다. 프론트 타입은 `StartPlanResult.phase`를 리터럴 유니온으로, 후보와 선호도 스키마를 더 구체적인 인터페이스로 표현한다.

## 엔드포인트–프론트 호출 대응표

| 메서드 | 백엔드 경로 및 선언 위치 | 요청 스키마 | 응답 스키마/형식 | 프론트 호출 위치 및 사용처 | 상태 |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/health` · `api/main.py:26` | 없음 | JSON `{"status":"ok"}` (`dict`; 명시적 `response_model` 없음) | 없음 | **프론트 미사용** |
| `POST` | `/api/plan/start` · `api/routes/plan.py:87` | JSON `PlanRequest` | JSON `StartPlanResponse` | `lovable/src/lib/api.ts:68` `startPlan` → `lovable/src/components/travel/TravelPlannerApp.tsx:203` | 사용 |
| `POST` | `/api/plan/resume` · `api/routes/plan.py:122` | JSON `ResumeRequest` | JSON `StartPlanResponse` | `lovable/src/lib/api.ts:78` `resumePlan` → `TravelPlannerApp.tsx:280,296` (선호도/날짜 선택) | 사용 |
| `POST` | `/api/plan/refine` · `api/routes/plan.py:157` | JSON `RefineRequest` | JSON `PlanResponse`; thread 없음/만료 시 `404` | `lovable/src/lib/api.ts:242` `refinePlan` → `TravelPlannerApp.tsx:359` | 사용 |
| `POST` | `/api/plan/resume/stream` · `api/routes/plan.py:182` | JSON `ResumeRequest` | `text/event-stream` SSE: `progress` 이벤트, `error` 이벤트 또는 `final` 이벤트(`StartPlanResponse` 필드 포함), 마지막 `data: [DONE]` | `lovable/src/lib/api.ts:94` `resumePlanStream` → `TravelPlannerApp.tsx:312` (숙소 선택 후) | 사용 |
| `POST` | `/api/plan` · `api/routes/plan.py:247` | JSON `PlanRequest` | JSON `PlanResponse` | `lovable/src/lib/api.ts:253` `createPlan`; 컴포넌트 참조 없음 | **프론트 함수 미사용** |
| `GET` | `/api/plan/stream` · `api/routes/plan.py:258` | 쿼리 `message: str` 필수; `budget`, `people`, `stay: str` 기본 `""` | `text/event-stream` SSE: `{step, status}` 진행 이벤트, 마지막 `{step: "synth", status, data: {...}}`, `data: [DONE]`. `data`는 `PlanResponse`와 유사하지만 `hotel_address`가 빠진 별도 payload | `lovable/src/lib/api.ts:176` `streamPlan`; 컴포넌트 참조 없음 | **프론트 함수 미사용** |

## 대응되지 않는 호출과 확인 사항

- **백엔드에 없는 프론트 API 호출: 없음.** `lovable/src/lib/api.ts`의 6개 URL은 모두 위 FastAPI 선언과 메서드가 일치한다.
- `lovable/src/server.ts:70,73`의 `fetch`는 TanStack 서버 엔트리로 요청을 전달하는 서버 핸들러이며 FastAPI에 대한 별도 호출이 아니다.
- `POST /api/plan`과 `GET /api/plan/stream`은 호출 래퍼가 있지만 현재 UI 컴포넌트에서 사용되지 않는다. `/health`는 호출 래퍼도 없다.
- `GET /api/plan/stream`의 마지막 `data`에는 `hotel_address`가 없지만 프론트 `streamPlan`은 이를 `PlanResult`로 취급한다. 해당 함수는 현재 UI에서 사용되지 않는다.
