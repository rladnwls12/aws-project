# 🌍 InternationalPay  Service - AWS Infrastructure & Deployment

> 확장 가능하고, 안전하며, 자동화된 결제 서비스 인프라 구축
> FastAPI 기반 애플리케이션 + AWS 클라우드 아키텍처

---

## 📌 Overview

이 프로젝트는 **Worldpay 서비스 운영을 위한 AWS 인프라 구성 및 배포 자동화 구조**를 제공합니다.

✔️ 보안 중심 설계 (KMS, VPC)
✔️ 고가용성 (ALB + Auto Scaling)
✔️ 운영 자동화 (Systemd + CloudWatch)
✔️ 확장 가능한 구조 (AMI 기반 배포)

---

## 🧭 Table of Contents

* [🏗 Architecture](#-architecture)
* [🔐 Security](#-security)
* [💻 Compute](#-compute)
* [⚙️ Deployment](#️-deployment)
* [📊 Logging](#-logging)
* [🚀 Scaling](#-scaling)
* [📄 Configuration](#-configuration)

---

## 🏗 Architecture

```
[User]
   ↓
[ALB]
   ↓
[Auto Scaling Group]
   ↓
[EC2 Instances (FastAPI)]
   ↓
[Aurora DB]
```

### 핵심 구조

* **ALB** → 트래픽 분산
* **ASG** → 자동 확장
* **EC2 (AMI 기반)** → 일관된 배포
* **Aurora** → 고성능 DB
* **CloudWatch** → 로그 & 모니터링

---

## 🔐 Security

### VPC & Network

* Private Subnet 기반 설계
* VPC Peering으로 내부 통신 분리

### Encryption (KMS)

* 모든 데이터 암호화
* 서비스별 CMK 분리

### ⚠️ 개선 권장 (중요)

현재 설정:

* `0.0.0.0/0` 전체 허용

👉 실무에서는 반드시 아래로 변경:

* Bastion → 특정 IP만 허용
* DB → Private 접근만 허용
* App → ALB만 접근 허용

---

## 💻 Compute

### Bastion Host

* EIP (고정 IP)
* SSH 접근 전용 서버

---

### Application Server

> Test EC2 → 검증 → AMI 생성 → 배포

#### IAM Role

* Secrets Manager
* KMS
* CloudWatch Logs

#### 패키지 설치

```bash
sudo yum install python-pip -y
pip3 install fastapi uvicorn
```

---

## ⚙️ Deployment

### Systemd Service

📍 `/etc/systemd/system/worldpay.service`

```ini
[Unit]
Description=worldpay service
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/home/ec2-user/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
StandardOutput=append:/home/ec2-user/worldpay.log
Restart=always

[Install]
WantedBy=multi-user.target
```

### 실행

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now worldpay
```

---

## 📊 Logging

### CloudWatch Logs

* 로그 파일: `/home/ec2-user/worldpay.log`
* 헬스체크 로그 제외 (`/health`)

```bash
sudo yum install amazon-cloudwatch-agent -y

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
-a fetch-config -m ec2 \
-c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

sudo systemctl restart amazon-cloudwatch-agent
```

---

## 🚀 Scaling

### AMI 기반 배포

* 검증된 EC2 → 이미지 생성
* 모든 서버 동일 환경 유지

---

### Auto Scaling Group

* Launch Template 사용
* ALB와 연결

✔️ 트래픽 증가 → 자동 확장
✔️ 장애 발생 → 자동 교체

---

## 📄 Configuration

### CloudWatch Agent

📍 `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ec2-user/worldpay.log",
            "log_group_name": "worldpay",
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

## 🧠 Design Philosophy

> “서버는 늘어나도, 복잡성은 늘어나면 안 된다.”

* 불변 인프라 (Immutable Infrastructure)
* 자동 복구 (Self-healing)
* 최소 권한 원칙 (Least Privilege)

---

## ⚡ Next Step (추천 발전 방향)

* Terraform으로 IaC 전환
* CI/CD (GitHub Actions)
* Blue/Green Deployment
* Redis 캐시 추가
* WAF 적용

---

## 🏁 Summary

이 구조는 단순한 서버 배포가 아니라:

👉 **“실제 서비스 운영 가능한 수준의 클라우드 아키텍처”**

를 목표로 설계되었습니다.

---


