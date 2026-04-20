# saml-inspector/keys

샌드박스 SAML SP (`stest-app`) 용 **개발 전용 자체서명 키페어** 입니다.

- `sp.crt` — Keycloak 이 이 SP 로부터 들어오는 서명된 AuthnRequest 를
  검증하기 위해 realm 설정에 임포트되는 공개 인증서.
- `sp.key` — 런타임에 pysaml2 가 사용하는 대응 개인키.

**이 키페어를 이 샌드박스 밖에서 재사용하지 마세요.** 재현성을 위해
레포에 커밋되어 있어 git 기록에 완전히 공개된 상태이므로 "이미 유출된
키" 로 간주해야 합니다. 재생성하려면:

```bash
openssl req -x509 -newkey rsa:2048 -keyout sp.key -out sp.crt \
    -days 3650 -nodes \
    -subj "/C=KR/O=Sandbox University/OU=KAFE Test Sandbox (DEV ONLY)/CN=stest.sandbox.ac.kr"
```

키를 교체한 경우 `keycloak/import.json` 의 대응 SAML 클라이언트 정의
(`attributes.saml.signing.certificate`) 에 새 공개 인증서 base64 값도
같이 넣어줘야 Keycloak 이 SP 서명을 검증할 수 있습니다.
