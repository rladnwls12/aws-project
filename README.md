# 🌍 InternationalPay Service Infrastructure Deployment Guide

본 문서는 **InternationalPay** 서비스의 고가용성(HA), 보안성, 확장성을 보장하기 위한 AWS 인프라 구성 및 애플리케이션 배포 표준 가이드입니다.

---

## 🏗️ 1. 아키텍처 개요 (Architecture Overview)

서비스는 **3-Tier 계층 구조**로 설계되어 있으며, 외부 노출을 최소화하고 리소스 간의 통신을 엄격히 통제합니다.

### 데이터 흐름

```
User → ALB (Public) → EC2 Auto Scaling Group (Private) → Aurora DB (Isolated)
```

### 주요 구성 요소

* **Networking**: VPC Peering을 통해 Private 자원 간의 전용 경로 확보
* **Security**: KMS CMK를 활용하여 EBS, Aurora, Secrets Manager 데이터 암호화
* **Compute**: AMI 기반 불변 인프라(Immutable Infrastructure)
* **Logging**: CloudWatch Agent 기반 중앙 로그 수집

---

## 🔐 2. 네트워크 및 보안 설정

### VPC & Routing

* VPC Peering을 통해 내부 통신은 인터넷을 거치지 않도록 구성
* KMS CMK를 서비스별로 분리 (App / DB / Log)

---

### 보안 그룹 (Security Group)

| 대상      | 포트      | 허용 소스      | 설명          |
| ------- | ------- | ---------- | ----------- |
| Bastion | 22      | Office IP  | 외부 접근 제한    |
| ALB     | 80, 443 | 0.0.0.0/0  | 퍼블릭 진입점     |
| App     | 8000    | ALB SG     | ALB 통해서만 접근 |
| App     | 22      | Bastion SG | 관리 접근       |
| DB      | 3306    | App SG     | 내부 통신만 허용   |

---

## 💾 3. 데이터베이스 구성 (AWS Aurora)

* 엔진: Aurora MySQL 3.x (MySQL 8.0 호환)
* 스토리지 암호화: KMS CMK 적용
* 서브넷: Multi-AZ Private Subnet 구성

### 가용성

* Backup: 최소 7일
* PITR 활성화

---

## 💻 4. 애플리케이션 구성 (Compute)

### IAM Role

* SecretsManagerReadWrite
* KMS Decrypt
* CloudWatchAgentServerPolicy

---

### 인스턴스 초기 설정

```bash
# 시스템 업데이트
sudo yum update -y

# 패키지 설치
sudo yum install python3.12 python3.12-pip amazon-cloudwatch-agent -y

# 애플리케이션 설치
cd /home/ec2-user
pip3.12 install -r requirements.txt
```

---

## ⚙️ 5. 서비스 등록 및 로깅

### Systemd 설정

📍 `/etc/systemd/system/worldpay.service`

```ini
[Unit]
Description=InternationalPay FastAPI Service
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/home/ec2-user/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
StandardOutput=append:/home/ec2-user/worldpay.log
StandardError=inherit
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

### CloudWatch Agent 설정

📍 `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ec2-user/worldpay.log",
            "log_group_name": "worldpay-prod",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "filters": [
              {
                "type": "exclude",
                "expression": ".*\\/health.*"
              }
            ]
          }
        ]
      }
    }
  }
}
```

---

## 🚀 6. 배포 전략 (Scaling & HA)

### AMI 생성 (Golden Image)

1. Test EC2에서 설정 완료
2. 재부팅 후 서비스 자동 실행 확인
3. AMI 생성

---

### Auto Scaling 구성

* Launch Template: AMI + IAM + SG 포함
* Target Group: Port 8000, `/health` 체크
* ASG:

  * 최소 2대 (Multi-AZ)
  * Auto Scaling 정책 적용

---

## ⚠️ 7. 운영 리스크 및 대응 (Ops Notes)

### 비용

* NAT Gateway 트래픽 비용 발생
* S3, DynamoDB → VPC Endpoint 권장

---

### 로그 관리

* CloudWatch Logs Retention 설정 필수
* 불필요 로그 제거 (/health 필터링)

---

### 보안 운영

* 0.0.0.0/0 정책 주기적 점검
* 접근 IP 최소화

---

## 🧠 8. 운영 철학 (Operational Principles)

> "문제는 발생하기 전에 대비하고, 발생하면 자동으로 복구된다."

* Immutable Infrastructure
* Self-Healing Architecture
* Least Privilege

---

## 🏁 Summary

이 인프라는 단순한 배포 환경이 아닌:

👉 **운영, 확장, 장애 대응까지 고려된 실전형 AWS 아키텍처**

를 목표로 설계되었습니다.
