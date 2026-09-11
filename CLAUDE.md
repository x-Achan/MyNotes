# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

This is an Obsidian vault serving as a personal digital archive and knowledge base for a software engineering graduate student (x-Achan, Beijing University of Technology). It is NOT a software project — there are no build commands, test suites, or package managers. The vault tracks three concurrent learning tracks: Java backend employment (priority), deep learning research (traffic video temporal object detection), and LeetCode algorithm practice.

## Vault Structure

```
00-个人数字档案/    — Long-term personal profile, current task board, update principles
01-力扣刷题笔记/    — LeetCode notes organized by technique (hash, two-pointer, sliding window, etc.)
02-深度学习代码笔记/ — Deep learning code study notes (VideoMamba, DINO, DETR)
03-深度学习实验记录/ — Experiment logs with training configs, results, and conclusions
04-Java学习笔记/    — Java/Spring Boot learning notes and project design docs
07-README/          — Research documentation: architecture walkthroughs, experiment plans, analysis docs
08-Prompt模板/      — Reusable prompt templates for AI-assisted learning and note formatting
09-其他/            — Misc (Markdown formatting, API configs — treat credentials as sensitive)
```

## Key Files to Read First

- `00-个人数字档案/个人技术画像.md` — Complete technical profile: skills, goals, project history, capability self-assessments (0-4 scale)
- `00-个人数字档案/当前阶段任务看板.md` — Current task board with checkboxes and verification criteria
- `00-个人数字档案/用户画像更新原则.md` — Strict rules for updating the profile (what belongs where, credibility tiers, versioning)
- `07-README/项目代码架构与训练流程全梳理.md` — Full VideoMamba-DINO architecture walkthrough (backbone → aggregator → SFP → temporal fusion → DINO head → loss)
- `07-README/EXPERIMENT_PLAN.md` — Phased experiment plan to improve mAP from ~4% to 20-30%
- `04-Java学习笔记/Java项目/AI_Learning_Profile_Platform_项目分阶段设计 (1).md` — AI Learning Profile Platform: staged Spring Boot project design (Phase 0-8)

## Conventions

### Content Separation (Critical)

The user enforces strict boundaries between file types. Do NOT mix content across these:

| Content type | Where it goes |
|---|---|
| Long-term identity, goals, skill levels | `00-个人数字档案/个人技术画像.md` |
| Current tasks, next steps, verification criteria | `00-个人数字档案/当前阶段任务看板.md` |
| Single LeetCode problem solutions | `01-力扣刷题笔记/` (by technique) |
| Experiment configs, loss, mAP, conclusions | `03-深度学习实验记录/` |
| Knowledge point explanations, code examples | `02-深度学习代码笔记/` or `04-Java学习笔记/` |
| AI code modifications | Experiment log or separate AI collaboration record |

### Profile Update Rules

- Only update `个人技术画像.md` when skill levels genuinely change (verified output required, not just "watched a video")
- Distinguish: **user-stated facts** (highest credibility) > **public work evidence** (careful wording) > **AI inference** (mark as judgment) > **unverified results** (mark as hypothesis)
- Never beautify capability scores; a score increase from 0→2 requires demonstrable output
- Update version number and add changelog entry on every update

### LeetCode Note Format

Follow the template in `08-Prompt模板/算法笔记标准格式.md`:
题目 / 题型 / 核心思路 / 为什么想到这个方法 / Java 代码模板 / 易错点 / 相似题

### Language

All content is written in Chinese. Maintain Chinese when editing or creating notes.

## Active Projects

### VideoMamba-DINO (Research)

Temporal object detection for UAV traffic surveillance video. VideoMamba (SSM backbone) + DINO detection head, targeting UAVDT and UA-DETRAC datasets. Current mAP ~4%, with a phased plan to reach 20-30% through bug fixes, temporal fusion improvements, multi-layer feature aggregation, and training config tuning. Training runs on a remote GPU server; experiment code lives in a separate repo.

### AI Learning Profile Platform (Java Backend)

Spring Boot project at GitHub `x-Achan/ai-learning-profile-backend`. Currently at Phase 0 (complete). Phased design spans 9 stages from basic Spring Boot hello-world through MySQL/MyBatis-Plus/JWT/Redis to AI API integration and Agent workflow. The project is both a real personal tool and a resume-building Java backend project.

## AI Collaboration Preferences

- Each AI interaction should target one clear goal
- AI must explain which files it will modify and why before making changes
- After modification, output a diff summary
- All code changes must be logged in experiment records
- Never trust AI's verbal estimates of metrics — only trust training logs, evaluation scripts, and visualization results
- Planning follows task stages with verification criteria, not fixed time schedules
