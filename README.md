# 🌍 InternationalPay Service - AWS Infrastructure & Deployment

> **확장 가능하고 안전하며 자동화된 결제 인프라 구축 가이드**
> FastAPI 애플리케이션 아키텍처 및 AWS 클라우드 배포 프로세스 정리

---

## 🧭 Table of Contents

1. [📌 Overview](#-overview)
2. [🏗 Architecture](#-architecture)
3. [🔐 Security & Network](#-security--network)
4. [💻 Compute & Application](#-compute--application)
5.  [💾 Database](#-database)
6. [🧪 개발 및 테스트](#-개발-및-테스트)
7. [⚙️ Deployment & Scaling](#️-deployment--scaling)
8. [📊 Logging & Monitoring](#-logging--monitoring)
9. [📄 Configuration Samples](#-configuration-samples)
10. [☁️ ALB / Target Group / ASG 상세 설정](#️-alb--target-group--asg-상세-설정)
11. [🧠 Design Philosophy](#-design-philosophy)
12. [🏁 Summary](#-summary)


---

## 📌 Overview

이 문서는 **InternationalPay 서비스** 운영을 위한 AWS 인프라 구성 및 배포 자동화 체계를 설명합니다.

- 보안 중심 설계 (KMS, VPC)
- 고가용성 (ALB + ASG)
- 운영 자동화 (Systemd + CloudWatch)
- 일관성 배포 (AMI 기반)

---

## 🏗 Architecture

웹/애플리케이션 계층과 데이터베이스 계층을 **총 2개의 개별 VPC로 분리**하여 보안 수준을 높입니다.  
외부 인터넷과 통신하는 애플리케이션 환경(VPC-1)과 내부에서만 통신하는 데이터베이스 환경(VPC-2)을 분리하며, 두 환경은 **VPC Peering**을 통해 논리적으로 연결됩니다.

```
인터넷 사용자
    ↓
ALB (VPC-1 Public Subnet AZ-a/b)
    ↓
EC2 ASG (VPC-1 Private Subnet AZ-a/b)
    ↓ [VPC Peering]
RDS Aurora (VPC-2 DB Subnet, Multi-AZ / 인터넷 통신 없음)
```

### VPC 구성

| VPC | 역할 | 서브넷 구성 |
|-----|------|------------|
| VPC-1 (애플리케이션) | 외부 트래픽 수신 및 앱 처리 | Public Subnet (AZ-a/b) — ALB<br>Private Subnet (AZ-a/b) — EC2 ASG |
| VPC-2 (데이터베이스) | DB 전용 격리 환경 | DB Subnet — RDS Multi-AZ (인터넷 통신 없음) |

### 구성 요소

| 컴포넌트 | 역할 |
|----------|------|
| ALB | 트래픽 분산 (VPC-1 Public Subnet) |
| ASG | 자동 확장 및 장애 복구 (VPC-1 Private Subnet) |
| VPC Peering | VPC-1 ↔ VPC-2 내부 통신 연결 |
| Aurora | 데이터 저장 및 복구 (VPC-2, 인터넷 차단) |
| CloudWatch | 로그 및 모니터링 |

---

## 🔐 Security & Network

### 네트워크 구성

- **VPC-1 (애플리케이션 VPC)**
  - Public Subnet (AZ-a, AZ-b): ALB 배치
  - Private Subnet (AZ-a, AZ-b): EC2 ASG 배치, NAT Gateway를 통한 외부 통신
- **VPC-2 (데이터베이스 VPC)**
  - DB Subnet: RDS Aurora Multi-AZ 배치, **인터넷 통신 완전 차단**
- **VPC Peering**: VPC-1 Private Subnet ↔ VPC-2 DB Subnet 간 내부 통신만 허용
  - 라우팅 테이블에 **Peering 경로** 반드시 추가 필요

### 보안 그룹

| 대상 | 포트 | 허용 소스 | VPC |
|------|------|-----------|-----|
| Bastion SG | 22 | 관리자 IP | VPC-1 |
| ALB SG | 80, 443 | 0.0.0.0/0 | VPC-1 |
| App SG | 8000 | ALB SG | VPC-1 |
| App SG | 22 | Bastion SG | VPC-1 |
| DB SG | 3306 | App SG (VPC-1 CIDR) | VPC-2 |

---


## 💻 Compute & Application

### **EC2 생성전에 DB섹션의 Db생성을 완료해주십쇼**

### Bastion

- SSH 접근 서버
- EIP 사용

### Application Server

- AMI 기반 배포
- IAM Role:
  - Secrets Manager - `GetSecretValue`  
    `#리소스 추가에서 SecretId에 /secret/db-* 으로 적용`
  - KMS - `kms:Decrypt`
  - CloudWatch Logs - `logs:CreateLogStream`, `logs:PutLogEvents`  
    `#클라우드 워치 로그 그룹 만든다음에 arn 주소 복붙`
-**인스턴스 프로파일 권한 부여**
### 환경 설치

```bash
sudo dnf install -y mariadb1011 python3.12 python3.12-pip
python3.12 -m pip install fastapi pydantic[email] pymysql boto3 sqlalchemy passlib uvicorn
```

---

## 💾 Database

### Aurora 설정

- **Engine**: Aurora MySQL (MySQL 8.0 호환)
- **배치**: VPC-2 DB Subnet (Multi-AZ), 인터넷 접근 완전 차단
- **접근**: VPC Peering을 통한 VPC-1 App Server만 허용

### 보안

- KMS CMK 기반 스토리지 암호화
- DB 직접 외부 접근 차단

### 로그 수집
- **모두 체크**

### 가용성

- 자동 백업 활성화 (≥ 7일)


### 스키마 생성

```sql
CREATE DATABASE worldpay;
USE worldpay;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  -- ...[원하는대로 작성]
);
```

### DB 연결 확인

RDS 엔드포인트로의 네트워크 및 접속 상태를 확인합니다.

```bash
# DNS 확인
nslookup worldpay-db-instance-1.creegaqoksh3.ap-northeast-2.rds.amazonaws.com

# 직접 접속 테스트
mysql -h worldpay-db.cluster-creegaqoksh3.ap-northeast-2.rds.amazonaws.com \
  -P 3306 -u admin -p
```
---

## 🧪 개발 및 테스트

### 1. main.py 작성

> **[대회 당일 지급 예정]** — 아래는 플레이스홀더입니다.

```python
# main.py
# ...[대회 당일 작성]
```

### 2. 의존성 파일 생성

```bash
pipreqs ./ --force
pip3.12 install -r requirements.txt
```

### 3. 수동 실행 및 API 테스트

`main.py` 작성 후 Uvicorn으로 직접 실행하여 동작을 확인합니다.

```bash
# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000
```

별도 터미널에서 API 응답을 확인합니다.

```bash
# 유저 생성
curl -X POST localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email":"a@gmail.com","name":"kim","password":"pass"}'

# 유저 조회
curl http://localhost:8000/users

# 헬스체크
curl localhost:8000/health
```

### 4. 로그 확인 및 디버깅

```bash
# 실시간 로그 확인
tail -f /home/ec2-user/worldpay.log

# systemd 서비스 로그 확인
sudo journalctl -u worldpay -f
```

---

## ⚙️ Deployment & Scaling

### 💿 AMI (Amazon Machine Image) 생성

운영 환경과 동일한 상태를 복제하여 확장 시 즉시 투입 가능한 이미지를 준비합니다.

- **기본 이미지**: Amazon Linux 2023 (Python 3.12 지원)
- **사전 설치 요소**:
  - Python 3.12, FastAPI, Uvicorn, Boto3
  - CloudWatch Agent (구성 파일 포함)
  - Systemd Service 등록 및 enable 처리
- **주의사항**:
  - `main.py` 등 소스 코드가 최신 상태인지 확인
  - `/home/ec2-user/worldpay.log` 파일 권한 설정 (ec2-user 소유)
  - 임시 파일 및 SSH 키 히스토리 삭제 후 이미지 생성
    ```bash
    shred -u ~/.ssh/authorized_keys
    ```

### Systemd 서비스 등록 및 관리

앱을 백그라운드 서비스로 등록하여 자동 실행되도록 설정합니다.

```bash
sudo vi /etc/systemd/system/worldpay.service
sudo systemctl daemon-reload
sudo systemctl enable --now worldpay
sudo systemctl status worldpay
```

`/etc/systemd/system/worldpay.service` 내용:

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
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### 배포 흐름 (Golden Image Workflow)

```
1. Update  : 테스트 EC2에서 최신 코드 반영 및 기능 검증
2. Bake    : 현재 상태 기반으로 신규 AMI 생성 (예: intlpay-v2-20231027)
3. Template: Launch Template 기본 버전을 신규 AMI ID로 업데이트
4. Refresh : ASG Instance Refresh로 순차적 교체 (Rolling Update) 시작
```

---

## 📊 Logging & Monitoring

### CloudWatch Agent 설치 및 실행

```bash
sudo dnf install amazon-cloudwatch-agent -y

sudo vim /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# 설정 적용
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

sudo systemctl restart amazon-cloudwatch-agent
```

### 로그 정책

- 로그 파일 경로: `/home/ec2-user/worldpay.log`
- `GET /health` 헬스체크 로그 제외 필터 적용

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
            "log_group_name": "[너의 로그 그룹 이름]",
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



## ☁️ ALB / Target Group / ASG 상세 설정

### 📋 Launch Template (시작 템플릿)

ASG가 인스턴스를 생성할 때 사용할 "설계도"입니다.

| 설정 항목 | 권장 설정 값 | 비고 |
|-----------|-------------|------|
| AMI ID | 위에서 생성한 Custom AMI | 버전 관리를 통해 롤백 지원 |
| Instance Type | t3.medium (지정된 거로) | CPU/Memory 집약도에 따라 선택 |
| IAM Instance Profile | **[님이 만든 Iam 역활]** | Secrets Manager, CloudWatch 권한 포함 |
| Security Groups | App-SG (80,8000 포트 허용) | ALB로부터의 인바운드만 허용 권장 |
| 암호화 활성화(KMS) | 성능 및 보안 준수 |

### 🎯 Target Group (대상 그룹)

ALB가 트래픽을 전달할 목적지들의 집합입니다.

- **Target Type**: Instances
- **Protocol / Port**: HTTP / 8000
- **Health Check**:
  - Path: `/health` (FastAPI 앱 내에 구현 필수)


### ⚖️ ALB (Application Load Balancer)

사용자의 요청을 받아 가용한 인스턴스로 분산합니다.

- **Scheme**: Internet-facing
- **배치**: VPC-1 Public Subnet (AZ-a, AZ-b) 각각 선택
- **Listeners**:
  - HTTP (80): HTTPS(443)로 Redirect 권장
  - HTTPS (443): ACM 인증서 적용 필수
- **Security Group**: ALB-SG (새로 생성)
  - Inbound: `0.0.0.0/0` (80, 443)
  - Outbound: `0.0.0.0`


### 🔄 ASG (Auto Scaling Group)

부하에 따라 인스턴스 개수를 자동으로 조절하고 고가용성을 유지합니다.

| 설정 항목 | 권장 설정 값 | 비고 |
|-----------|-------------|------|
| VPC & Subnets | VPC-1 Private Subnets (AZ-a, AZ-b) | 보안을 위해 외부 직접 노출 차단 |
| Desired Capacity | 2 | 최소 가용성 확보 (Multi-AZ) |
| Minimum Capacity | 2 | 장애 시에도 서비스 유지 |
| Maximum Capacity | 4~6 | 트래픽 폭증 대비 상한선 |
| 추가 설정 | CloudWatch 그룹 지표 수집 활성화 | 로그 쌓기 위함 |


#### 📈 Scaling Policy

- **Target Tracking Scaling**
  - Metric: Average CPU Utilization
  - Target Value: **50%**

    
### Tag 설정
| Key   | Value |
|--------|----------|
| Name | [주어진 이름] |


## 🧠 Design Philosophy

- **보안 우선**: 모든 컴포넌트는 최소 권한 원칙에 따라 격리
- **고가용성**: ALB + ASG를 통한 무중단 확장 및 자동 복구
- **운영 자동화**: Systemd & CloudWatch로 수동 개입 최소화
- **일관성 있는 배포**: AMI → Launch Template → ASG 파이프라인으로 환경 드리프트 방지
- **Zero Downtime**: Instance Refresh로 가동 중 순차 교체, 다운타임 없음

---

## 🏁 Summary

| 항목 | 내용 |
|------|------|
| 런타임 | Python 3.12 + FastAPI + Uvicorn |
| 컴퓨팅 | EC2 + ASG + ALB |
| 데이터베이스 | Aurora MySQL 8.0 (Multi-AZ) |
| 보안 | KMS CMK, VPC, Secrets Manager |
| 모니터링 | CloudWatch Logs + Agent |
| 배포 방식 | AMI 기반 Launch Template + Instance Refresh |

---
