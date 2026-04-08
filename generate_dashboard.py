def fetch_issues():
    headers = get_headers()
    headers["Content-Type"] = "application/json"

    # 인증 확인
    print("🔐 인증 사용자 확인 중...")
    me_resp = requests.get(f"https://{JIRA_DOMAIN}/rest/api/3/myself", headers=headers, timeout=30)
    print(f"   응답: {me_resp.status_code}")
    if me_resp.ok:
        me = me_resp.json()
        print(f"   ✅ 인증 성공! 사용자: {me.get('displayName')} ({me.get('emailAddress')})")
    else:
        print(f"   ❌ 인증 실패: {me_resp.text[:200]}")
        print("   → GitHub Secret(JIRA_EMAIL, JIRA_TOKEN) 값을 확인해주세요!")
        return []

    # 핵심 JQL: 하이브리드러닝 프로젝트 + 김하영 + 운영중
    search_url = f"https://{JIRA_DOMAIN}/rest/api/3/search/jql"
    jql = f'project = "하이브리드러닝 프로젝트" AND assignee = "{ASSIGNEE_ID}" AND status = "운영중" ORDER BY updated DESC'
    
    print(f"\n🔍 조회 JQL: {jql}")
    payload = {
        "jql": jql,
        "maxResults": 100,
        "fields": ["summary", "status", "priority", "updated", "duedate", "description", "comment", "labels"]
    }
    resp = requests.post(search_url, headers=headers, json=payload, timeout=30)
    print(f"   응답: {resp.status_code}")
    
    if resp.ok:
        issues = resp.json().get("issues", [])
        total = resp.json().get("total", 0)
        print(f"   결과: {len(issues)}건 (전체 {total}건)")
        if issues:
            print(f"✅ 성공! {len(issues)}건 조회 완료")
            return issues
        else:
            print("⚠️ 조건에 맞는 이슈 없음 — 상태명 확인 중...")
            # 상태명이 다를 경우 대비해 확인용 조회
            check_payload = {
                "jql": f'project = "하이브리드러닝 프로젝트" AND assignee = "{ASSIGNEE_ID}" ORDER BY updated DESC',
                "maxResults": 5,
                "fields": ["summary", "status"]
            }
            check_resp = requests.post(search_url, headers=headers, json=check_payload, timeout=30)
            if check_resp.ok:
                for iss in check_resp.json().get("issues", []):
                    print(f"   - 상태: [{iss['fields']['status']['name']}] {iss['fields']['summary'][:40]}")
    else:
        print(f"   ❌ 조회 실패: {resp.text[:200]}")

    print("\n⚠️ 빈 대시보드로 생성합니다.")
    return []
