# OIDC Reference

샌드박스 Keycloak이 발급하는 모든 **OIDC claim의 이름 · 타입 · 분배 위치**를 한 곳에 모은 레퍼런스. `keycloak/import.json`의 `oidc-kafe-profile` client scope 및 내장 매퍼와 1:1 대응한다. SAML 쪽은 [`saml.md`](saml.md) 참조.

- **이름 규약**: camelCase (REFEDS OIDCre/SSP OIDC 모듈 기본값과 일치 — snake_case 번역 없음).
- **분배 원칙 (P3)**: ID token에는 프로토콜 claim만, 사용자 attribute는 `/userinfo`로만 내보냄. `access_token`은 기본적으로 비움.
- **출처 scope**: `openid` · `profile` · `email` 은 Keycloak 빌트인, `oidc-kafe-profile`은 이 샌드박스의 커스텀 scope.


## 핵심 개념

* **P3 원칙 (Privacy-Preservation Policy)**: 토큰 크기를 줄이고 프라이버시를 보호하기 위해 정보를 쪼개서 전달하는 원칙.
    - **ID Token**: 최소한의 인증 정보만 포함 (`sub`, `iss`, `aud` 등).
    - **UserInfo**: 실제 사용자 속성 (`email`, `eduPerson*` 등) 은 이 주소로 따로 요청해야 전달됨.
    - **Access Token**: 사용자 속성 비움.
* **`oidc-kafe-profile`**: KAFE 호환 claim 매퍼가 전부 들어있는 Keycloak 클라이언트 스코프. 새 OIDC SP 는 이 스코프만 할당하면 KAFE 와 동일한 속성 집합을 받습니다.
* **Claim Inspector (`otest-app`)**: IdP 가 발급한 OIDC 토큰과 userinfo 응답을 한 화면에서 확인하는 디버깅 도구 — http://otest.sandbox.ac.kr/ .


## 전체 claim 분배 표

| User Attribute | OIDC Claim | Type | ID token | UserInfo | Access token | Multivalued | Scope |
|---|---|---|:-:|:-:|:-:|:-:|---|
| (builtin) `sub` | `sub` | string | ✓ | ✓ | ✓ | — | `openid` |
| `uid` | `preferred_username` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `firstName` | `given_name` | string | ✗ | ✓ | ✗ | no | `profile` |
| `lastName` | `family_name` | string | ✗ | ✓ | ✗ | no | `profile` |
| `displayName` | `name` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `email` | `email` | string | ✗ | ✓ | ✗ | no | `email` |
| `emailVerified` | `email_verified` | boolean | ✗ | ✓ | ✗ | no | `email` |
| `eduPersonPrincipalName` | `eduPersonPrincipalName` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `eduPersonUniqueId` | `eduPersonUniqueId` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `eduPersonAffiliation` | `eduPersonAffiliation` | JSON array | ✗ | ✓ | ✗ | **yes** | `oidc-kafe-profile` |
| `eduPersonScopedAffiliation` | `eduPersonScopedAffiliation` | JSON array | ✗ | ✓ | ✗ | **yes** | `oidc-kafe-profile` |
| `eduPersonEntitlement` | `eduPersonEntitlement` | JSON array | ✗ | ✓ | ✗ | **yes** | `oidc-kafe-profile` |
| `eduPersonOrcid` | `eduPersonOrcid` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `schacHomeOrganization` | `schacHomeOrganization` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `schacHomeOrganizationType` | `schacHomeOrganizationType` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `schacPersonalUniqueCode` | `schacPersonalUniqueCode` | JSON array | ✗ | ✓ | ✗ | **yes** | `oidc-kafe-profile` |
| `o` | `o` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `ou` | `ou` | string | ✗ | ✓ | ✗ | no | `oidc-kafe-profile` |
| `isMemberOf` | `isMemberOf` | JSON array | ✗ | ✓ | ✗ | **yes** | `oidc-kafe-profile` |

**주의할 점**: Keycloak 기본 `email` scope 매퍼의 "Add to ID token"이 ON인데, 이 샌드박스에서는 **OFF로 꺼둠**. 이게 KAFE(SimpleSAMLphp OIDC 모듈 v2+)의 `alwaysAddClaimsToIdToken=false` 기본 동작과 일치시키는 핵심 포인트.


## 샘플 payload — alice

`claim-inspector`에서 alice (`student`)로 로그인한 결과.

### ID token payload (프로토콜 claim만)
```json
{
  "iss": "http://iam.sandbox.ac.kr/realms/sandbox",
  "aud": "claim-inspector",
  "azp": "claim-inspector",
  "sub": "b1a2...<uuid>",
  "typ": "ID",
  "exp": 1734567890,
  "iat": 1734567590,
  "nonce": "...",
  "sid": "...",
  "auth_time": 1734567590
}
```

ID token에는 `email`, `preferred_username`, `eduPerson*`, `schac*` **전부 없음** — 이게 P3 원칙.

### UserInfo 응답 (풀셋)
```json
{
  "sub": "b1a2...<uuid>",
  "preferred_username": "alice",
  "name": "Alice Anderson",
  "given_name": "Alice",
  "family_name": "Anderson",
  "email": "alice@sandbox.ac.kr",
  "email_verified": true,
  "eduPersonPrincipalName": "alice@sandbox.ac.kr",
  "eduPersonUniqueId": "alice-1a2b3c4d@sandbox.ac.kr",
  "eduPersonAffiliation": ["member", "student"],
  "eduPersonScopedAffiliation": ["member@sandbox.ac.kr", "student@sandbox.ac.kr"],
  "eduPersonEntitlement": ["urn:mace:sandbox.ac.kr:entitlement:lms-user"],
  "schacHomeOrganization": "sandbox.ac.kr",
  "schacHomeOrganizationType": "urn:schac:homeOrganizationType:kr:university",
  "schacPersonalUniqueCode": ["urn:schac:personalUniqueCode:kr:sandbox.ac.kr:studentID:20260001"],
  "o": "Sandbox University",
  "ou": "Department of Computer Science",
  "isMemberOf": ["cn=cs-undergrad,ou=groups,dc=sandbox,dc=ac,dc=kr"]
}
```

실시간으로 확인: http://otest.sandbox.ac.kr/me → 로그인 후 `/me.json`에서 전체 응답 덤프 가능.


## 정규식 검증 힌트 (pytest에서 재사용)

| Claim | 정규식 |
|---|---|
| `eduPersonScopedAffiliation` 값 | `^(faculty|student|staff|employee|member|affiliate|library-walk-in)@[a-zA-Z0-9.-]+$` |
| `schacHomeOrganizationType` | `^urn:schac:homeOrganizationType:[a-z]{2,}:[a-zA-Z0-9.-]+$` |
| `eduPersonPrincipalName` | `^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$` |


## 왜 이 분배 정책인가

- **ID token 최소화**: ID token은 모든 토큰 요청 시 RP에 전달됨. 사용자 attribute를 넣으면 불필요하게 계속 전송됨 + 크기 비대 + 변경 시 즉시 반영 안 됨.
- **UserInfo 권위**: RP가 "지금 이 사용자"의 attribute를 확정 필요 시 access token으로 `/userinfo` 호출 → Keycloak이 현재 값 반환. Outline/Indico 등 성숙한 OIDC RP의 관행.
- **KAFE 호환**: KAFE 프로덕션(SSP OIDC v2+)의 `alwaysAddClaimsToIdToken=false` 기본값과 동일.


## 새 OIDC SP 추가하기

새로운 서비스를 연동하려면 IdP에 OIDC 클라이언트를 등록해야 합니다.

- **AI 와 함께 확장**: `keycloak/import.json` 에는 `claim-inspector` (Flask), `outline` (Wiki) 등 참조 예시가 있습니다. 기존 블록을 복사해서 Claude/GPT 에게 *"이 형식 참고해서 내 앱 주소로 OIDC 클라이언트를 추가해줘"* 라고 요청해도 됩니다.
- **설정 반영**: 수정 후 `./scripts/reset.sh` 로 realm 재임포트.
- **Client Secret 조회**: `./scripts/print-secrets.sh` 가 등록된 모든 클라이언트의 비밀값을 자동으로 출력합니다.

```bash
./scripts/print-secrets.sh    # 클라이언트 시크릿 일괄 조회
./scripts/reset.sh            # 데이터 완전 초기화 및 재임포트
docker compose ps             # 컨테이너 상태 요약
```


## 관련 파일

- `keycloak/import.json` — 매퍼 정의 원본
- `claim-inspector/app.py` `/me` — 분배를 UI로 렌더
- `tests/test_claims_distribution.py` — P3 원칙 회귀 가드
