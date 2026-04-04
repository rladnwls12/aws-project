# 🌍 InternationalPay Service - AWS Infrastructure & Deployment

> **확장 가능하고 안전하며 자동화된 결제 인프라 구축 가이드**
> FastAPI 애플리케이션 아키텍처 및 AWS 클라우드 배포 프로세스 정리

---

## 🧭 Table of Contents

1. [📌 Overview](#-overview)
2. [🏗 Architecture](#-architecture)
3. [🔐 Security & Network](#-security--network)
4. [💾 Database](#-database)
5. [💻 Compute & Application](#-compute--application)
6. [⚙️ Deployment & Scaling](#-deployment--scaling)
7. [📊 Logging & Monitoring](#-logging--monitoring)
8. [📄 Configuration Samples](#-configuration-samples)
9. [🧠 Design Philosophy](#-design-philosophy)
10. [🏁 Summary](#-summary)

---

## 📌 Overview

이 문서는 **InternationalPay 서비스** 운영을 위한 AWS 인프라 구성 및 배포 자동화 체계를 설명합니다.

- 보안 중심 설계 (KMS, VPC)
- 고가용성 (ALB + ASG)
- 운영 자동화 (Systemd + CloudWatch)
- 일관성 배포 (AMI 기반)

---

## 🏗 Architecture

```
User → ALB (Public) → EC2 ASG (Private) → Aurora DB (Isolated)
```

### 구성 요소

| 컴포넌트 | 역할 |
|----------|------|
| ALB | 트래픽 분산 |
| ASG | 자동 확장 및 장애 복구 |
| Aurora | 데이터 저장 및 복구 지원 |
| CloudWatch | 로그 및 모니터링 |

---

## 🔐 Security & Network

### 네트워크

- Public / Private Subnet 분리
- VPC Peering 내부 통신

### 보안 그룹

| 대상 | 포트 | 허용 |
|------|------|------|
| Bastion | 22 | 관리자 IP |
| App | 8000 | [자유 Default: 0.0.0.0] |
| DB | 3306 | [자유 Default:main.vpc IP|



---

## 💾 Database

### Aurora 설정

- **Engine**: Aurora MySQL (MySQL 8.0 호환)
- **배치**: Private Subnet (Multi-AZ)
- **접근**: App Server만 허용

### 보안

- KMS CMK 기반 스토리지 암호화
- DB 직접 외부 접근 차단

### 가용성

- 자동 백업 활성화 (≥ 7일)
- PITR (Point-in-Time Recovery) 활성화

---

## 💻 Compute & Application

### Bastion

- SSH 접근 서버
- EIP 사용

### Application Server

- AMI 기반 배포
- IAM Role:
  - Secrets Manager - GetSecretValue
  - KMS - kms:Decrypt
  - CloudWatch Logs - "logs:CreateLogStream" "logs:PutLogEvents" #클라우드 워치 로그 그룹 만든다음에 arn 주소 복붙

### 설치

```bash
sudo dnf install python3.12 python3.12-pip -y
pip3.12 install fastapi uvicorn boto3 pipreqs
pipreqs ./ --force
pip3.12 install -r requirements.txt
```

---

## ⚙️ Deployment & Scaling

### Systemd 서비스 설정

```ini
[Unit]
Description=InternationalPay FastAPI Service
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

### 배포 흐름

```
Test EC2 구성 → AMI 생성 → Launch Template 적용 → ASG 배포
```

---

## 📊 Logging & Monitoring

### CloudWatch Agent 설치 및 실행

```bash
sudo dnf install amazon-cloudwatch-agent -y

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

sudo systemctl restart amazon-cloudwatch-agent
```

### 로그 정책

- 로그 파일 경로: `/home/ec2-user/worldpay.log`

---

## 📄 Configuration Samples

### CloudWatch Agent 설정 (`amazon-cloudwatch-agent.json`)

```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ec2-user/worldpay.log",
            "log_group_name": "international-pay-logs",
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

- **보안 우선**: 모든 컴포넌트는 최소 권한 원칙에 따라 격리
- **고가용성**: ALB + ASG를 통한 무중단 확장 및 자동 복구
- **운영 자동화**: Systemd & CloudWatch로 수동 개입 최소화
- **일관성 있는 배포**: AMI → Launch Template → ASG 파이프라인으로 환경 드리프트 방지

---

## 🏁 Summary

| 항목 | 내용 |
|------|------|
| 런타임 | Python 3.12 + FastAPI + Uvicorn |
| 컴퓨팅 | EC2 + ASG + ALB |
| 데이터베이스 | Aurora MySQL 8.0 (Multi-AZ) |
| 보안 | KMS CMK, VPC, Secrets Manager |
| 모니터링 | CloudWatch Logs + Agent |
| 배포 방식 | AMI 기반 Launch Template |
