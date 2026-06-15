"""Test script: sends a certificate generation request and polls for completion."""
import json
import time
import urllib.request

API_BASE = "http://localhost:8000"

def generate_certificate():
    payload = {
        "category": "1",
        "issuedAt": "1403-01-15",
        "certificateNumber": "001",
        "certificationId": "TEST-CERT-001",
        "user": {
            "userId": "test-user-1",
            "gender": "Male",
            "firstName": "علی",
            "lastName": "محمدی",
            "nationalId": "0012345678",
        },
        "course": {
            "courseCode": "CS-101",
            "name": "دوره آموزشی پایتون",
            "organizingUnit": "واحد آموزش",
            "date": "1403-01-15",
            "time": "10:00",
            "signatory": {
                "userId": "sign-1",
                "gender": "Male",
                "firstName": "احمد",
                "lastName": "رضایی",
                "position": "مدیر آموزش",
                "signature": "https://placehold.co/200x60?text=Signature",
            },
            "unitStamp": "https://placehold.co/200x200?text=Stamp",
        },
        "qr_url": "https://example.com/cert/TEST-CERT-001",
    }

    req = urllib.request.Request(
        f"{API_BASE}/certificates/generate/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"Submitted: {json.dumps(result, indent=2)}")
            return result["job_id"]
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.read().decode()}")
        return None

def poll_status(job_id, timeout=60, interval=3):
    print(f"\nPolling job {job_id}...")
    for _ in range(timeout // interval):
        try:
            with urllib.request.urlopen(f"{API_BASE}/certificates/status/{job_id}") as resp:
                data = json.loads(resp.read())
                print(f"  Status: {data.get('status', 'unknown')}")
                if data.get("status") in ("completed", "failed"):
                    return data
        except urllib.error.HTTPError:
            pass
        time.sleep(interval)
    print("  Timed out waiting for completion.")
    return None

if __name__ == "__main__":
    job_id = generate_certificate()
    if job_id:
        result = poll_status(job_id)
        if result:
            print(f"\nFinal result: {json.dumps(result, indent=2)}")
            if result.get("status") == "completed":
                print(f"\nCertificate file_id: {result.get('file_id')}")
                print(f"Download URL: {API_BASE}/certificates/download/{result.get('file_id')}")
