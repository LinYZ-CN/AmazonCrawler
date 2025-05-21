import requests

cookies = {
    'x-hng': 'lang=zh-CN&domain=sellercentral.amazon.co.uk',
    'appguard-cookie-consent': 'operational%7Cperformance%7Cadvertising',
    'session-id': '261-5340826-5234657',
    'i18n-prefs': 'GBP',
    'ubid-acbuk': '260-5838401-4465113',
    'lc-acbuk': 'en_GB',
    'session-token': '"uSdqWQDkaFj18kgUYXtGta1kDTRxv0VFDKRbvxO+POOKYwRylFqtSZnKBQU+ng9KeQWGKJRdPl04ee1P6d0d/tv06xzoDwBb5yI+2Kj7V5KlQTz4iG+xmpLPxS3WnJihkerVcaqeuFTreW8wtv0u0SyhMiSmrz8LrzisJ/PydC1A7kjUHFxcgJ6Z018Osti9GwaUhZPLjZN8zv/7dSTGid918kyEWo2cHePwwcajTr6qgXWgTaRZE1wtdTL5Ov2UYALf8bdBp7iznE62nMCNfGEM+KVNSyS8iB/rs7HOZyfqzCydgn+SGL63p3+8I4eABA5C8AyljZvp0+OUaPEzzPJQWqQmx8AKkdliBkpqVPA="',
    'session-id-time': '2378357065l',
    'ph_phc_tGCcl9SINhy3N0zy98fdlWrc1ppQ67KJ8pZMzVZOECH_posthog': '%7B%22distinct_id%22%3A%220196e749-2603-7ba3-98c6-91708564865f%22%2C%22%24sesid%22%3A%5B1747637122726%2C%220196e749-2688-7ef7-9b23-eecee2fe4b99%22%2C1747637053064%5D%7D',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,ko;q=0.6,ar;q=0.5',
    'anti-csrftoken-a2z': '',
    'content-type': 'application/json; charset=UTF-8',
    'origin': 'https://sellercentral.amazon.co.uk',
    'priority': 'u=1, i',
    'referer': 'https://sellercentral.amazon.co.uk/fba/profitabilitycalculator/index?lang=en_GB',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    # 'cookie': 'x-hng=lang=zh-CN&domain=sellercentral.amazon.co.uk; appguard-cookie-consent=operational%7Cperformance%7Cadvertising; session-id=261-5340826-5234657; i18n-prefs=GBP; ubid-acbuk=260-5838401-4465113; lc-acbuk=en_GB; session-token="uSdqWQDkaFj18kgUYXtGta1kDTRxv0VFDKRbvxO+POOKYwRylFqtSZnKBQU+ng9KeQWGKJRdPl04ee1P6d0d/tv06xzoDwBb5yI+2Kj7V5KlQTz4iG+xmpLPxS3WnJihkerVcaqeuFTreW8wtv0u0SyhMiSmrz8LrzisJ/PydC1A7kjUHFxcgJ6Z018Osti9GwaUhZPLjZN8zv/7dSTGid918kyEWo2cHePwwcajTr6qgXWgTaRZE1wtdTL5Ov2UYALf8bdBp7iznE62nMCNfGEM+KVNSyS8iB/rs7HOZyfqzCydgn+SGL63p3+8I4eABA5C8AyljZvp0+OUaPEzzPJQWqQmx8AKkdliBkpqVPA="; session-id-time=2378357065l; ph_phc_tGCcl9SINhy3N0zy98fdlWrc1ppQ67KJ8pZMzVZOECH_posthog=%7B%22distinct_id%22%3A%220196e749-2603-7ba3-98c6-91708564865f%22%2C%22%24sesid%22%3A%5B1747637122726%2C%220196e749-2688-7ef7-9b23-eecee2fe4b99%22%2C1747637053064%5D%7D',
}

params = {
    'countryCode': 'GB',
    'locale': 'en-GB',
}

json_data = {
    'keywords': 'B0DZT1D6N4',
    'countryCode': 'GB',
    'searchType': 'GENERAL',
    'pageOffset': 1,
}

response = requests.post(
    'https://sellercentral.amazon.co.uk/rcpublic/searchproduct',
    params=params,
    cookies=cookies,
    headers=headers,
    json=json_data,
)
print(response.status_code)
print(response.text)