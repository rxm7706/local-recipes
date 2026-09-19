# LF AI & Data Foundation — Hosted Projects Reference

**Last Updated**: June 2026  
**Sources**: [landscape.lfai.foundation](https://landscape.lfai.foundation) (`landscape.yml`, lfai/lfai-landscape) · [lfaidata.foundation/projects](https://lfaidata.foundation/projects/) · install/availability verified against PyPI + conda-forge feedstocks  
**Scope**: The **57 currently-hosted** LF AI & Data Foundation projects (Graduated · Incubating · Sandbox). Archived / retired projects are excluded.  
**Purpose**: Reference guide for LF AI & Data hosted projects — category, maturity, and **how to install & use each one** — for architecture decisions and ecosystem documentation.

> Maturity stages reflect the official LF AI & Data project lifecycle: **Sandbox** (early) → **Incubating** (growing adoption & governance) → **Graduated** (mature, widely adopted). Repos and categories come from `landscape.yml`; maturity stages from the foundation's official projects directory; install methods verified against PyPI + conda-forge.

---

## Maturity Summary

| Stage | Count | Projects |
|---|---|---|
| 🎓 Graduated | 12 | Adversarial Robustness Toolbox (ART), Angel ML, DocArray, Egeria, Flyte, Horovod, Kedro, Marquez, Milvus, ONNX, OpenLineage, Pyro |
| 🐣 Incubating | 26 | Adlik, AI Explainability 360, AI Fairness 360, Amundsen, BeeAI, Bitol, Data Prep Kit, Datashim, Delta Lake, Docling, Elyra, FATE, Feast, ForestFlow, JanusGraph, Kompute, Ludwig, NNStreamer, Open Voice Interoperability Initiative, Open Voice Network TrustMark, OpenDS4All, RWKV, SOAJS, sparklyr, Substra, Vortex |
| 🧪 Sandbox | 19 | Artigraph, CLAIMED, DeepCausality, DeepRec, DLRover, Feathr, FlagAI, IREE, LakeSoul, Machine Learning eXchange (MLX), Monocle, OAAX, Open Model Initiative, Open Platform for Enterprise AI (OPEA), OpenFL, Recommenders, Ryoma, SapientML, Unity Catalog |

**Total active hosted projects: 57** (12 Graduated · 26 Incubating · 19 Sandbox)

---

## Installability at a Glance

How each of the 57 is consumed (verified June 2026 against PyPI + conda-forge feedstocks):

| Channel | Count | Notes |
|---|---|---|
| **pip + conda-forge** | 20 | install either way |
| **conda-forge only** | 1 | `sparklyr` → `r-sparklyr` (R package; no PyPI) |
| **pip only** | 20 | conda-forge packaging gap → see [Book of Work](#book-of-work--conda-forge-packaging-gap) |
| **platform / other** | 11 | Docker / Helm / JVM / npm / cargo / apt / source |
| **spec / docs only** | 5 | nothing to install (standards & courseware) |

**Installable in some form: 52 of 57.** Directly package-installable (pip or conda): **41**. On conda-forge today: **21**.

---

## Data

### DocArray — 🎓 Graduated
**Description**: Represent, send, store and search multimodal data

**Install**: pip · conda — `pip install docarray` · `conda install -c conda-forge docarray`  
**Use**: `from docarray import BaseDoc, DocList` — represent, store and search multimodal data.  
**GitHub**: https://github.com/docarray/docarray · **Homepage**: https://docarray.jina.ai/ · **Landscape**: Data / Store & Format

### Egeria — 🎓 Graduated
**Description**: Egeria core

**Install**: JVM platform (Java 17: `./gradlew clean build`, or Docker `odpi/egeria-platform`) · Python client `pip install pyegeria` — *pyegeria not on conda-forge (gap)*  
**Use**: Run the OMAG Server Platform; drive metadata/governance via REST or pyegeria.  
**GitHub**: https://github.com/odpi/egeria · **Homepage**: https://egeria-project.org · **Landscape**: Data / Governance

### Marquez — 🎓 Graduated
**Description**: Collect, aggregate, and visualize a data ecosystem's metadata

**Install**: server `git clone …/marquez && ./docker/up.sh` (Docker/Helm) · client `pip install marquez-python` · `conda install -c conda-forge marquez-python`  
**Use**: Open the Web UI at `localhost:3000`; collects lineage emitted via OpenLineage.  
**GitHub**: https://github.com/MarquezProject/marquez · **Homepage**: https://marquezproject.github.io/marquez · **Landscape**: Data / Operations

### Milvus — 🎓 Graduated
**Description**: Milvus is a high-performance, cloud-native vector database built for scalable vector ANN search

**Install**: server `bash standalone_embed.sh start` (Docker/Helm) · client `pip install pymilvus` · `conda install -c conda-forge pymilvus` · embedded `pip install milvus-lite`  
**Use**: `from pymilvus import MilvusClient` — scalable vector ANN search.  
**GitHub**: https://github.com/milvus-io/milvus · **Homepage**: https://milvus.io · **Landscape**: Data / Store & Format

### OpenLineage — 🎓 Graduated
**Description**: An Open Standard for lineage metadata collection

**Install**: pip · conda — `pip install openlineage-python` · `conda install -c conda-forge openlineage-python`  
**Use**: Emit lineage events from the client / integrations (Airflow, Spark, dbt).  
**GitHub**: https://github.com/OpenLineage/OpenLineage · **Homepage**: https://github.com/OpenLineage · **Landscape**: Data / Lineage

### Amundsen — 🐣 Incubating
**Description**: Amundsen is a metadata driven application for improving the productivity of data analysts, data scientists and engineers when interacting with data.

**Install**: app via Docker/Helm · metadata lib `pip install amundsen-databuilder` · `conda install -c conda-forge amundsen-databuilder`  
**Use**: Ingest metadata via amundsen-databuilder; browse it in the Amundsen app.  
**GitHub**: https://github.com/amundsen-io/amundsen · **Homepage**: https://www.amundsen.io/ · **Landscape**: Data / Operations

### Bitol — 🐣 Incubating
**Description**: Home of the Open Data Contract Standard (ODCS).

**Install**: pip — `pip install open-data-contract-standard` — *not on conda-forge (gap)*  
**Use**: Author & validate data contracts in the Open Data Contract Standard (ODCS).  
**GitHub**: https://github.com/bitol-io/open-data-contract-standard · **Homepage**: https://bitol.io · **Landscape**: Data / Governance

### Datashim — 🐣 Incubating
**Description**: A kubernetes based framework for hassle free handling of datasets

**Install**: Kubernetes — `kubectl apply` the Datashim operator — *no pip/conda*  
**Use**: Declare Datasets as Kubernetes CRDs to mount data into pods.  
**GitHub**: https://github.com/datashim-io/datashim · **Homepage**: https://github.com/datashim-io/datashim · **Landscape**: Data / Operations

### Delta Lake — 🐣 Incubating
**Description**: An open-source storage framework that enables building a Lakehouse architecture with compute engines including Spark, PrestoDB, Flink, Trino, and Hive and APIs

**Install**: pip · conda — `pip install deltalake` · `conda install -c conda-forge deltalake`  
**Use**: `from deltalake import DeltaTable` (or delta-spark) — ACID lakehouse storage.  
**GitHub**: https://github.com/delta-io/delta · **Homepage**: https://delta.io/ · **Landscape**: Data / Store & Format

### Docling — 🐣 Incubating
**Description**: Get your documents ready for gen AI

**Install**: pip · conda — `pip install docling` · `conda install -c conda-forge docling`  
**Use**: `from docling.document_converter import DocumentConverter` — parse docs for GenAI.  
**GitHub**: https://github.com/docling-project/docling · **Homepage**: https://research.ibm.com/blog/docling-generative-AI · **Landscape**: Data / Store & Format

### Feast — 🐣 Incubating
**Description**: The Open Source Feature Store for AI/ML

**Install**: pip · conda — `pip install feast` · `conda install -c conda-forge feast`  
**Use**: `feast apply` → serve features for training & inference.  
**GitHub**: https://github.com/feast-dev/feast · **Homepage**: https://feast.dev/ · **Landscape**: Data / Feature Engineering

### JanusGraph — 🐣 Incubating
**Description**: JanusGraph: an open-source, distributed graph database

**Install**: download distribution / Docker `janusgraph/janusgraph`; query via Gremlin — *no pip/conda*  
**Use**: Connect over Gremlin (gremlinpython / console) to query the graph.  
**GitHub**: https://github.com/JanusGraph/janusgraph · **Homepage**: https://janusgraph.org/ · **Landscape**: Data / Store & Format

### NNStreamer — 🐣 Incubating
**Description**: Neural Network (NN) Streamer, Stream Processing Paradigm for Neural Network Apps/Devices.

**Install**: `apt install nnstreamer` (Ubuntu PPA) / build · Android/Tizen — *no pip/conda*  
**Use**: Build neural-network pipelines as GStreamer plugins on-device.  
**GitHub**: https://github.com/nnstreamer/nnstreamer · **Homepage**: https://nnstreamer.ai/ · **Landscape**: Data / Stream Processing

### OpenDS4All — 🐣 Incubating
**Description**: OpenDS4All project, hosted by LF AI & Data

**Install**: courseware — `git clone` the repo (slides + notebooks)  
**Use**: Teach / learn data science from the open courseware.  
**GitHub**: https://github.com/odpi/OpenDS4All · **Homepage**: https://github.com/odpi/OpenDS4All · **Landscape**: Data / Education

### Vortex — 🐣 Incubating
**Description**: An extensible, high-performance columnar file format and toolkit for fast random access and compute, designed for data-lake and database storage.

**Install**: pip — `pip install vortex-array` — *not on conda-forge (gap)*  
**Use**: Python bindings (`vortex-array`) for the Vortex columnar format.  
**GitHub**: https://github.com/vortex-data · **Homepage**: https://vortex.dev/ · **Landscape**: Data / Store & Format

### Artigraph — 🧪 Sandbox
**Description**: Batteries included toolkit for data engineering.

**Install**: pip · conda — `pip install arti` · `conda install -c conda-forge arti`  
**Use**: Python toolkit for data engineering / artifact graphs.  
**GitHub**: https://github.com/artigraph/artigraph · **Homepage**: https://github.com/artigraph/ · **Landscape**: Data / Pipeline Management

### Feathr — 🧪 Sandbox
**Description**: Feathr – A scalable, unified data and AI engineering platform for enterprise

**Install**: pip · conda — `pip install feathr` · `conda install -c conda-forge feathr`  
**Use**: Python feature store / feature-engineering platform.  
**GitHub**: https://github.com/linkedin/feathr · **Homepage**: https://github.com/linkedin/feathr · **Landscape**: Data / Feature Engineering

### LakeSoul — 🧪 Sandbox
**Description**: LakeSoul is an end-to-end, realtime cloud-native Lakehouse framework for fast data ingestion, concurrent updates, incremental analytics, multimodal data processing and vector search — powering next-generation BI and AI workloads.

**Install**: pip — `pip install lakesoul` — *not on conda-forge (gap)*  
**Use**: Python API to the LakeSoul realtime lakehouse (Spark/Flink core).  
**GitHub**: https://github.com/meta-soul/LakeSoul · **Homepage**: https://www.dmetasoul.com/en/docs/lakesoul/ · **Landscape**: Data / Store & Format

### Unity Catalog — 🧪 Sandbox
**Description**: Open, Multi-modal Catalog for Data & AI

**Install**: server `bin/start-uc-server` (download/JVM) or Docker · Python client `pip install unitycatalog-client` — *not on conda-forge (gap)*  
**Use**: Python client to a Unity Catalog server — open governance for data & AI.  
**GitHub**: https://github.com/unitycatalog/unitycatalog · **Homepage**: https://www.unitycatalog.io/ · **Landscape**: Data / Governance

---

## Model

### Flyte — 🎓 Graduated
**Description**: Dynamic, resilient AI orchestration. Coordinate data, models, and compute as you build AI workflows.

**Install**: pip · conda — `pip install flytekit` · `conda install -c conda-forge flytekit`  
**Use**: `@task`/`@workflow` in Python → `pyflyte run`; `flytectl demo start` for a local cluster.  
**GitHub**: https://github.com/flyteorg/flyte · **Homepage**: https://flyte.org · **Landscape**: Model / Workflow

### Horovod — 🎓 Graduated
**Description**: Distributed training framework for TensorFlow, Keras, PyTorch, and Apache MXNet.

**Install**: pip · conda — `pip install horovod` · `conda install -c conda-forge horovod`  
**Use**: Wrap your optimizer (`hvd.DistributedOptimizer`) and launch with `horovodrun -np N`.  
**GitHub**: https://github.com/horovod/horovod · **Homepage**: https://horovod.ai/ · **Landscape**: Model / Training

### Kedro — 🎓 Graduated
**Description**: Kedro is a toolbox for production-ready data science. It uses software engineering best practices to help you create data engineering and data science pipelines that are reproducible, maintainable, and modular.

**Install**: pip · conda — `pip install kedro` · `conda install -c conda-forge kedro`  
**Use**: `kedro new` → `kedro run` — reproducible, modular data-science pipelines.  
**GitHub**: https://github.com/kedro-org/kedro · **Homepage**: https://kedro.org/ · **Landscape**: Model / Workflow

### ONNX — 🎓 Graduated
**Description**: Open standard for machine learning interoperability

**Install**: pip · conda — `pip install onnx` · `conda install -c conda-forge onnx`  
**Use**: `import onnx; onnx.load('model.onnx')` — portable model interchange (runtime: onnxruntime).  
**GitHub**: https://github.com/onnx/onnx · **Homepage**: https://onnx.ai/ · **Landscape**: Model / Format & Interface

### Adlik — 🐣 Incubating
**Description**: Adlik: Toolkit for Accelerating Deep Learning Inference

**Install**: build from source / Docker — *no pip/conda*  
**Use**: Compile and serve deep-learning models for cloud & embedded inference.  
**GitHub**: https://github.com/Adlik/Adlik · **Homepage**: https://adlik.ai/ · **Landscape**: Model / Inference

### FATE — 🐣 Incubating
**Description**: An Industrial Grade Federated Learning Framework

**Install**: platform via Docker / KubeFATE · Python client `pip install fate-client` — *not on conda-forge (gap)*  
**Use**: Submit federated-learning jobs to a FATE cluster via fate-client.  
**GitHub**: https://github.com/FederatedAI/FATE · **Homepage**: https://www.fedai.org/ · **Landscape**: Model / Federated Learning

### Ludwig — 🐣 Incubating
**Description**: Low-code framework for building custom LLMs, neural networks, and other AI models

**Install**: pip — `pip install ludwig` — *not on conda-forge (gap)*  
**Use**: `ludwig train --config config.yaml` — declarative, low-code model building.  
**GitHub**: https://github.com/ludwig-ai/ludwig · **Homepage**: https://ludwig-ai.github.io/ludwig-docs/ · **Landscape**: Model / Training

### Substra — 🐣 Incubating
**Description**: Low-level Python library used to interact with a Substra network

**Install**: pip — `pip install substra` — *not on conda-forge (gap)*  
**Use**: Python client to orchestrate federated/distributed ML across partners.  
**GitHub**: https://github.com/Substra/substra · **Homepage**: https://github.com/Substra/substra · **Landscape**: Model / Federated Learning

### CLAIMED — 🧪 Sandbox
**Description**: The goal of CLAIMED is to enable low-code/no-code rapid prototyping style programming to seamlessly CI/CD into production.

**Install**: pip — `pip install claimed` — *not on conda-forge (gap)*  
**Use**: Compose reusable CLAIMED components into low-code pipelines.  
**GitHub**: https://github.com/claimed-framework/component-library · **Homepage**: https://github.com/claimed-framework/ · **Landscape**: Model / Workflow

### DLRover — 🧪 Sandbox
**Description**: DLRover: An Automatic Distributed Deep Learning System

**Install**: pip — `pip install dlrover` — *not on conda-forge (gap)*  
**Use**: `dlrover-run …` — elastic, fault-tolerant distributed training.  
**GitHub**: https://github.com/intelligent-machine-learning/dlrover · **Homepage**: https://github.com/intelligent-machine-learning/dlrover · **Landscape**: Model / Training

### FlagAI — 🧪 Sandbox
**Description**: FlagAI (Fast LArge-scale General AI models) is a fast, easy-to-use and extensible toolkit for large-scale model.

**Install**: pip — `pip install flagai` — *not on conda-forge (gap)*  
**Use**: Train and use large-scale general AI models.  
**GitHub**: https://github.com/BAAI-Open/FlagAI · **Homepage**: https://github.com/BAAI-Open/FlagAI · **Landscape**: Model / Tool

### Machine Learning eXchange (MLX) — 🧪 Sandbox
**Description**: Machine Learning eXchange (MLX). Data and AI Assets Catalog and Execution Engine

**Install**: deploy on Kubernetes (Tekton) / Docker — *no pip/conda; not the Apple `mlx` PyPI package*  
**Use**: Catalog and execute ML assets/pipelines on Kubernetes.  
**GitHub**: https://github.com/machine-learning-exchange/mlx · **Homepage**: https://www.ml-exchange.org/ · **Landscape**: Model / Marketplace

### OpenFL — 🧪 Sandbox
**Description**: An Open Framework for Federated Learning.

**Install**: pip · conda — `pip install openfl` · `conda install -c conda-forge openfl`  
**Use**: `fx` CLI — federated learning without sharing data.  
**GitHub**: https://github.com/intel/openfl · **Homepage**: https://openfl.readthedocs.io/en/latest · **Landscape**: Model / Federated Learning

---

## Machine Learning

### Angel ML — 🎓 Graduated
**Description**: A Flexible and Powerful Parameter Server for large-scale machine learning

**Install**: download release / build from source · run on Spark/YARN · Docker — *no pip/conda*  
**Use**: Submit Parameter-Server ML jobs to a Spark/YARN cluster.  
**GitHub**: https://github.com/Angel-ML/angel · **Homepage**: https://angelml.ai/ · **Landscape**: Machine Learning / Platform

### Data Prep Kit — 🐣 Incubating
**Description**: Open source project for data preparation for GenAI applications

**Install**: pip — `pip install data-prep-toolkit` — *not on conda-forge (gap)*  
**Use**: Run data-prep transforms/pipelines to make data LLM-ready.  
**GitHub**: https://github.com/data-prep-kit/data-prep-kit · **Homepage**: https://developer.ibm.com/components/data-prep-kit/ · **Landscape**: Machine Learning / Framework

### ForestFlow — 🐣 Incubating
**Description**: ForestFlow is a policy-driven Machine Learning Model Server.

**Install**: JVM model server — Docker / Helm — *no pip/conda*  
**Use**: Deploy & serve ML models via REST/gRPC (policy-driven).  
**GitHub**: https://github.com/ForestFlow/ForestFlow · **Homepage**: https://forestflow.ai · **Landscape**: Machine Learning / Platform

### DeepCausality — 🧪 Sandbox
**Description**: Dynamic Causality in Rust

**Install**: Rust crate — `cargo add deep_causality` — *no pip/conda*  
**Use**: `use deep_causality::*;` — context-aware causal reasoning in Rust.  
**GitHub**: https://github.com/deepcausality-rs/deep_causality · **Homepage**: https://DeepCausality.com · **Landscape**: Machine Learning / Library

### IREE — 🧪 Sandbox
**Description**: A retargetable MLIR-based machine learning compiler and runtime toolkit.

**Install**: pip — `pip install iree-base-compiler` — *not on conda-forge (gap)*  
**Use**: `iree-compile model.mlir` + iree-base-runtime to execute (MLIR ML compiler).  
**GitHub**: https://github.com/iree-org/iree · **Homepage**: https://www.iree.dev/ · **Landscape**: Machine Learning / Library

### OAAX — 🧪 Sandbox
**Description**: Open AI Accelerator Exchange — an open standard that simplifies development and deployment of edge-AI applications via a unified framework for converting and optimizing ML models across accelerators.

**Install**: open standard + conversion toolchains (Docker) — no single package  
**Use**: Convert/optimize models to the OAAX runtime for edge accelerators.  
**GitHub**: https://github.com/OAAX-standard · **Homepage**: https://www.oaax.org · **Landscape**: Machine Learning / Framework

### Open Platform for Enterprise AI (OPEA) — 🧪 Sandbox
**Description**: Generative AI Examples is a collection of GenAI examples such as ChatQnA, Copilot, which illustrate the pipeline capabilities of the Open Platform for Enterprise AI (OPEA) project.

**Install**: Docker Compose / Helm (GenAIExamples, GenAIComps) — *no single pip/conda*  
**Use**: Deploy composable GenAI microservice pipelines (e.g. ChatQnA).  
**GitHub**: https://github.com/opea-project/GenAIExamples · **Homepage**: https://opea.dev · **Landscape**: Machine Learning / Platform

### Recommenders — 🧪 Sandbox
**Description**: Best Practices on Recommendation Systems

**Install**: pip — `pip install recommenders` — *not on conda-forge (gap)*  
**Use**: Best-practice recommender-system utilities & example notebooks.  
**GitHub**: https://github.com/microsoft/recommenders · **Homepage**: https://microsoft-recommenders.readthedocs.io/ · **Landscape**: Machine Learning / Library

### SapientML — 🧪 Sandbox
**Description**: Generative AutoML for Tabular Data

**Install**: pip — `pip install sapientml` — *not on conda-forge (gap)*  
**Use**: `from sapientml import SapientML` — AutoML for tabular data.  
**GitHub**: https://github.com/sapientml/sapientml · **Homepage**: https://github.com/sapientml/sapientml · **Landscape**: Machine Learning / Library

---

## Deep Learning

### DeepRec — 🧪 Sandbox
**Description**: DeepRec is a high-performance recommendation deep learning framework based on TensorFlow.

**Install**: build from source (TensorFlow fork) / Docker images — *no pip/conda*  
**Use**: Drop-in TF1.15-compatible engine for large-scale recommenders.  
**GitHub**: https://github.com/alibaba/DeepRec · **Homepage**: https://deeprec.readthedocs.io/ · **Landscape**: Deep Learning / Framework

### Ryoma — 🧪 Sandbox
**Description**: Common AI agent framework solving your data problems

**Install**: pip — `pip install ryoma-ai` — *not on conda-forge (gap)*  
**Use**: AI agent framework for data tasks (SQL / analytics).  
**GitHub**: https://github.com/project-ryoma/ryoma · **Homepage**: https://github.com/project-ryoma/ryoma · **Landscape**: Deep Learning / Framework

---

## Generative AI

### BeeAI — 🐣 Incubating
**Description**: Build production-ready AI agents in both Python and Typescript.

**Install**: pip — `pip install beeai-framework` — *not on conda-forge (gap)*  
**Use**: Build production AI agents in Python or TypeScript.  
**GitHub**: https://github.com/i-am-bee/beeai-framework · **Homepage**: https://www.ibm.com/think/news/beeai-open-source-multiagent · **Landscape**: Generative AI / Tools

### RWKV — 🐣 Incubating
**Description**: RWKV infctx trainer, for training arbitary context sizes, to 10k and beyond!

**Install**: pip — `pip install rwkv` — *not on conda-forge (gap)*  
**Use**: `from rwkv.model import RWKV` — run RWKV (RNN with transformer-level performance) LLMs.  
**GitHub**: https://github.com/RWKV/RWKV-infctx-trainer · **Homepage**: https://www.rwkv.com · **Landscape**: Generative AI / Models

### Monocle — 🧪 Sandbox
**Description**: Monocle is a framework for tracing GenAI app code. This repo contains implementation of Monocle for GenAI apps written in Python.

**Install**: pip — `pip install monocle_apptrace` — *not on conda-forge (gap)*  
**Use**: `from monocle_apptrace import setup_monocle_telemetry` — trace GenAI apps.  
**GitHub**: https://github.com/monocle2ai/monocle · **Homepage**: http://monocle2ai.org/ · **Landscape**: Generative AI / Tools

### Open Model Initiative — 🧪 Sandbox
**Description**: A repository for establishing and maintaining standardized model formats across the open-source media ecosystem.

**Install**: open model-format standards — nothing to install  
**Use**: Adopt OMI open model-format standards for media generation.  
**GitHub**: https://github.com/Open-Model-Initiative/OMI-Model-Standards · **Homepage**: https://github.com/orgs/Open-Model-Initiative/ · **Landscape**: Generative AI / Models

---

## Trusted & Responsible AI

### Adversarial Robustness Toolbox (ART) — 🎓 Graduated
**Description**: Adversarial Robustness Toolbox (ART) - Python Library for Machine Learning Security - Evasion, Poisoning, Extraction, Inference - Red and Blue Teams

**Install**: pip · conda — `pip install adversarial-robustness-toolbox` · `conda install -c conda-forge adversarial-robustness-toolbox`  
**Use**: Python library to attack/defend ML models (evasion, poisoning, extraction, inference).  
**GitHub**: https://github.com/Trusted-AI/adversarial-robustness-toolbox · **Homepage**: https://developer.ibm.com/open/projects/adversarial-robustness-toolbox/ · **Landscape**: Trusted & Responsible AI / Adversarial

### AI Explainability 360 — 🐣 Incubating
**Description**: Interpretability and explainability of data and machine learning models

**Install**: pip — `pip install aix360` — *not on conda-forge (gap)*  
**Use**: Python toolkit for model interpretability & explainability.  
**GitHub**: https://github.com/Trusted-AI/AIX360 · **Homepage**: http://aix360.mybluemix.net · **Landscape**: Trusted & Responsible AI / Explainability

### AI Fairness 360 — 🐣 Incubating
**Description**: A comprehensive set of fairness metrics for datasets and machine learning models, explanations for these metrics, and algorithms to mitigate bias in datasets and models.

**Install**: pip · conda — `pip install aif360` · `conda install -c conda-forge aif360`  
**Use**: Python toolkit for fairness metrics & bias mitigation.  
**GitHub**: https://github.com/Trusted-AI/AIF360 · **Homepage**: https://developer.ibm.com/open/projects/ai-fairness-360/ · **Landscape**: Trusted & Responsible AI / Bias & Fairness

### Open Voice Network TrustMark — 🐣 Incubating
**Description**: Translates ethical principles into actionable practice for conversational-AI systems through a community TrustMark program.

**Install**: program / docs — nothing to install  
**Use**: Apply the TrustMark ethical-AI guidelines to conversational systems.  
**GitHub**: https://github.com/Open-Voice-Trustmark/docs · **Homepage**: https://openvoicenetwork.org/trustmark-initiative/ · **Landscape**: Trusted & Responsible AI / Bias & Fairness

---

## Distributed Computing

### Open Voice Interoperability Initiative — 🐣 Incubating
**Description**: Developing the "Message Envelope" / Open Floor — a universal, open API for interoperability between voice assistants, chatbots, and language models (analogous to HTTP/HTML for conversational AI).

**Install**: specification — nothing to install (implement the Open Floor / Message-Envelope API)  
**Use**: Implement the open Message-Envelope / Open-Floor API for assistant interop.  
**GitHub**: https://github.com/open-voice-interoperability · **Homepage**: https://openvoicenetwork.org/interoperability-initiative/ · **Landscape**: Distributed Computing / Interface

### SOAJS — 🐣 Incubating
**Description**: Open-source microservices and API management platform for building and productizing multi-tenant SaaS applications.

**Install**: `npm install soajs` (Node) / Docker — *no pip/conda*  
**Use**: Build & operate multi-tenant microservices / APIs.  
**GitHub**: https://github.com/soajs/soajs · **Homepage**: https://www.soajs.org/ · **Landscape**: Distributed Computing / Computing & Management

### sparklyr — 🐣 Incubating
**Description**: R interface for Apache Spark

**Install**: conda · R — `conda install -c conda-forge r-sparklyr` · `install.packages("sparklyr")` (CRAN) — *no pip*  
**Use**: `library(sparklyr)` — R interface to Apache Spark.  
**GitHub**: https://github.com/sparklyr/sparklyr · **Homepage**: https://sparklyr.ai · **Landscape**: Distributed Computing / Interface

---

## Programming

### Pyro — 🎓 Graduated
**Description**: Deep universal probabilistic programming with Python and PyTorch

**Install**: pip · conda — `pip install pyro-ppl` · `conda install -c conda-forge pyro-ppl`  
**Use**: `import pyro` — deep probabilistic programming on PyTorch.  
**GitHub**: https://github.com/pyro-ppl/pyro · **Homepage**: http://pyro.ai/ · **Landscape**: Programming / Programming

### Kompute — 🐣 Incubating
**Description**: General purpose GPU compute framework built on Vulkan to support 1000s of cross vendor graphics cards (AMD, Qualcomm, NVIDIA & friends). Blazing fast, mobile-enabled, asynchronous and optimized for advanced GPU data processing usecases. Backed by the Linux Foundation.

**Install**: pip · conda — `pip install kp` · `conda install -c conda-forge kompute`  
**Use**: `import kp` — general-purpose cross-vendor GPU compute (Vulkan).  
**GitHub**: https://github.com/KomputeProject/kompute · **Homepage**: https://kompute.cc · **Landscape**: Programming / Programming

---

## Notebook Environment

### Elyra — 🐣 Incubating
**Description**: Elyra extends JupyterLab with an AI centric approach.

**Install**: pip · conda — `pip install elyra` · `conda install -c conda-forge elyra`  
**Use**: `jupyter lab` — visual pipelines & AI tooling inside JupyterLab.  
**GitHub**: https://github.com/elyra-ai/elyra · **Homepage**: https://elyra.readthedocs.io/en/latest · **Landscape**: Notebook Environment / Notebook Environment

---

## Book of Work — conda-forge Packaging Gap

The **20 hosted projects that are pip-installable but NOT yet on conda-forge** — i.e. candidate feedstocks to create. Verified June 2026 (PyPI present; no conda-forge feedstock under any common spelling). PyPI version shown is the latest at time of check.

| # | Project | Stage | PyPI package | Latest | Install command |
|---|---------|-------|--------------|--------|-----------------|
| 1 | Egeria | Graduated | `pyegeria` | 6.0.15.4 | `pip install pyegeria` |
| 2 | AI Explainability 360 | Incubating | `aix360` | 0.3.0 | `pip install aix360` |
| 3 | BeeAI | Incubating | `beeai-framework` | 0.1.81 | `pip install beeai-framework` |
| 4 | Bitol | Incubating | `open-data-contract-standard` | 3.1.2 | `pip install open-data-contract-standard` |
| 5 | Data Prep Kit | Incubating | `data-prep-toolkit` | 1.1.7 | `pip install data-prep-toolkit` |
| 6 | FATE | Incubating | `fate-client` | 2.2.0 | `pip install fate-client` |
| 7 | Ludwig | Incubating | `ludwig` | 0.17.5 | `pip install ludwig` |
| 8 | RWKV | Incubating | `rwkv` | 0.8.32 | `pip install rwkv` |
| 9 | Substra | Incubating | `substra` | 1.0.0 | `pip install substra` |
| 10 | Vortex | Incubating | `vortex-array` | 0.32.0 | `pip install vortex-array` |
| 11 | CLAIMED | Sandbox | `claimed` | 0.2.7 | `pip install claimed` |
| 12 | DLRover | Sandbox | `dlrover` | 0.6.1 | `pip install dlrover` |
| 13 | FlagAI | Sandbox | `flagai` | 1.8.4 | `pip install flagai` |
| 14 | IREE | Sandbox | `iree-base-compiler` | 3.11.0 | `pip install iree-base-compiler` |
| 15 | LakeSoul | Sandbox | `lakesoul` | 1.0.2 | `pip install lakesoul` |
| 16 | Monocle | Sandbox | `monocle_apptrace` | 0.8.4 | `pip install monocle_apptrace` |
| 17 | Recommenders | Sandbox | `recommenders` | 1.2.1 | `pip install recommenders` |
| 18 | Ryoma | Sandbox | `ryoma-ai` | 0.1.5 | `pip install ryoma-ai` |
| 19 | SapientML | Sandbox | `sapientml` | 0.4.17 | `pip install sapientml` |
| 20 | Unity Catalog | Sandbox | `unitycatalog-client` | 0.5.0 | `pip install unitycatalog-client` |

> Note: a few of these are *clients* of a platform project (e.g. `pyegeria` for Egeria, `fate-client` for FATE, `unitycatalog-client` for Unity Catalog) — packaging the client is still the actionable conda-forge contribution.

---

## How to Use This Reference

1. **For Architecture Reviews** — the categorized structure shows the LF AI & Data hosted-project offerings per functional area.
2. **For Maturity Assessment** — the badge (🎓 Graduated · 🐣 Incubating · 🧪 Sandbox) signals adoption/governance maturity; prefer Graduated/Incubating for production.
3. **For Installation** — each entry's **Install** line gives the verified pip/conda/other command; **Use** gives the entry point.
4. **For conda-forge Contribution** — the [Book of Work](#book-of-work--conda-forge-packaging-gap) lists the 20 pip-only projects that still need a feedstock.
5. **For Ecosystem Lookup** — the appendix indexes every software item in the landscape (each name links to its repo).

---

## Additional Resources

- **Official Landscape**: https://landscape.lfai.foundation
- **Landscape data (`landscape.yml`)**: https://github.com/lfai/lfai-landscape
- **Projects Directory (by maturity)**: https://lfaidata.foundation/projects/
- **LF AI & Data Foundation**: https://lfaidata.foundation
- **GitHub Organization**: https://github.com/lfai
- **Community**: https://lfaidata.foundation/community/

---

## Appendix — Full LF AI & Data Landscape (Software)

An alphabetical index of **all 367 software items** tracked in the LF AI & Data landscape (LF-hosted projects *plus* third-party / ecosystem tools). Member companies and hosting companies are excluded. Each name links to its source repository (or homepage where no repo is listed). Format: `Name: Category | Subcategory`.

Counts by category: Data (107) · Model (64) · Machine Learning (45) · Deep Learning (36) · Natural Language Processing (25) · Trusted & Responsible AI (21) · Distributed Computing (20) · Programming (16) · Notebook Environment (12) · Reinforcement Learning (10) · Generative AI (6) · Security & Privacy (5).

1) [1chipML](https://github.com/1chipML/1chipML): Machine Learning | Library
2) [Accord.NET](https://github.com/accord-net/framework): Machine Learning | Framework
3) [Acumos](https://github.com/acumos/documentation): Model | Marketplace
4) [Adlik](https://github.com/Adlik/Adlik): Model | Inference
5) [AdvBox](https://github.com/advboxes/AdvBox): Trusted & Responsible AI | Adversarial
6) [Adversarial Robustness Toolbox (ART)](https://github.com/Trusted-AI/adversarial-robustness-toolbox): Trusted & Responsible AI | Adversarial
7) [Advertorch](https://github.com/BorealisAI/advertorch): Trusted & Responsible AI | Adversarial
8) [Aequitas](https://github.com/dssg/aequitas): Trusted & Responsible AI | Bias & Fairness
9) [AI Explainability 360](https://github.com/Trusted-AI/AIX360): Trusted & Responsible AI | Explainability
10) [AI Fairness 360](https://github.com/Trusted-AI/AIF360): Trusted & Responsible AI | Bias & Fairness
11) [AIMET](https://github.com/quic/aimet): Model | Tool
12) [ALBERT](https://github.com/google-research/ALBERT): Natural Language Processing | Natural Language Processing
13) [ALIBI](https://github.com/SeldonIO/alibi): Trusted & Responsible AI | Explainability
14) [Alink](https://github.com/alibaba/Alink): Machine Learning | Platform
15) [AllenNLP](https://github.com/allenai/allennlp): Natural Language Processing | Natural Language Processing
16) [Alluxio](https://github.com/alluxio/alluxio): Data | Store & Format
17) [Amundsen](https://github.com/amundsen-io/amundsen): Data | Operations
18) [Analytics Zoo](https://github.com/intel-analytics/analytics-zoo): Data | Pipeline Management
19) [Angel ML](https://github.com/Angel-ML/angel): Machine Learning | Platform
20) [Apache Airflow](https://github.com/apache/airflow): Model | Workflow
21) [Apache Ambari](https://github.com/apache/ambari): Distributed Computing | Computing & Management
22) [Apache Bahir](https://github.com/apache/bahir): Distributed Computing | Computing & Management
23) [Apache Drill](https://github.com/apache/drill): Data | SQL Engine
24) [Apache Hive](https://github.com/apache/hive): Data | Operations
25) [Apache Iceberg](https://github.com/apache/iceberg): Data | Store & Format
26) [Apache Mesos](https://github.com/apache/mesos): Distributed Computing | Computing & Management
27) [Apache Nifi](https://github.com/apache/nifi): Model | Workflow
28) [Apache Oozie](https://github.com/apache/oozie): Data | Pipeline Management
29) [Apache ORC](https://github.com/apache/orc): Data | Store & Format
30) [Apache Ranger](https://github.com/apache/ranger): Distributed Computing | Computing & Management
31) [Apache RocketMQ](https://github.com/apache/rocketmq): Data | Stream Processing
32) [Apache SINGA](https://github.com/apache/singa): Deep Learning | Framework
33) [Apache Spark](https://github.com/apache/spark): Distributed Computing | Computing & Management
34) [Apache Storm](https://github.com/apache/storm): Distributed Computing | Computing & Management
35) [Apache SystemML](https://github.com/apache/systemds): Machine Learning | Platform
36) [Apache Toree](https://github.com/apache/incubator-toree): Distributed Computing | Interface
37) [Apache UIMA](https://github.com/apache/uima-uimaj): Natural Language Processing | Natural Language Processing
38) [Apache Zeppelin](https://github.com/apache/zeppelin): Notebook Environment | Notebook Environment
39) [AresDB](https://github.com/uber/aresdb): Data | Store & Format
40) [Argo](https://github.com/argoproj/argo-workflows): Model | Workflow
41) [Armada](https://github.com/armadaproject/armada): Distributed Computing | Computing & Management
42) [Arrow](https://github.com/apache/arrow): Data | Store & Format
43) [Artigraph](https://github.com/artigraph/artigraph): Data | Pipeline Management
44) [Audit AI](https://github.com/pymetrics/audit-ai): Trusted & Responsible AI | Bias & Fairness
45) [AutoGen](https://github.com/microsoft/autogen): Machine Learning | Framework
46) [AutoGluon](https://github.com/awslabs/autogluon): Machine Learning | Library
47) [Avro](https://github.com/apache/avro): Data | Store & Format
48) [AX](https://github.com/facebook/Ax): Machine Learning | Platform
49) [Azkaban](https://github.com/azkaban/azkaban): Model | Workflow
50) [BeakerX](https://github.com/twosigma/beakerx): Notebook Environment | Notebook Environment
51) [Beam](https://github.com/apache/beam): Data | Stream Processing
52) [BeeAI](https://github.com/i-am-bee/beeai-framework): Generative AI | Tools
53) [BentoML](https://github.com/bentoml/BentoML): Model | Workflow
54) [BERT](https://github.com/google-research/bert): Natural Language Processing | Natural Language Processing
55) [BeyondML](https://github.com/Beyond-ML-Labs/mann): Deep Learning | Tool
56) [BigDL](https://github.com/intel-analytics/BigDL): Deep Learning | Library
57) [Bitol](https://github.com/bitol-io/open-data-contract-standard): Data | Governance
58) [bokeh](https://github.com/bokeh/bokeh): Data | Visualization
59) [BoTorch](https://github.com/pytorch/botorch): Deep Learning | Tool
60) [Brooklin](https://github.com/linkedin/Brooklin): Data | Stream Processing
61) [Cadence](https://github.com/uber/cadence): Model | Workflow
62) [Candle](https://github.com/huggingface/candle): Machine Learning | Framework
63) [Captum](https://github.com/pytorch/captum): Trusted & Responsible AI | Explainability
64) [Carbon](https://github.com/carbon-design-system/carbon): Data | Visualization
65) [Catalyst](https://github.com/catalyst-team/catalyst): Deep Learning | Library
66) [CatBoost](https://github.com/catboost/catboost): Machine Learning | Library
67) [CausalML](https://github.com/uber/causalml): Model | Inference
68) [Ceph](https://github.com/ceph/ceph): Data | Store & Format
69) [Chainer](https://github.com/chainer/chainer): Deep Learning | Framework
70) [Chainer RL](https://github.com/chainer/chainerrl): Reinforcement Learning | Reinforcement Learning
71) [CKAN](https://github.com/ckan/ckan): Data | Operations
72) [CLAIMED](https://github.com/claimed-framework/component-library): Model | Workflow
73) [CleanRL](https://github.com/vwxyzjn/cleanrl): Reinforcement Learning | Reinforcement Learning
74) [CleverHans](https://github.com/cleverhans-lab/cleverhans): Trusted & Responsible AI | Adversarial
75) [Clipper](https://github.com/ucbrise/clipper): Model | Tool
76) [CNTK](https://github.com/Microsoft/CNTK): Deep Learning | Framework
77) [Coach](https://github.com/IntelLabs/coach): Reinforcement Learning | Reinforcement Learning
78) [Colaboratory](https://github.com/googlecolab/colabtools): Notebook Environment | Notebook Environment
79) [Community Data License Agreement (CDLA)](https://github.com/lfai/CDLA): Data | Governance
80) [Computer Vision Annotation Tool (CVAT)](https://github.com/openvinotoolkit/cvat): Data | Labeling & Annotation
81) [CoreNLP](https://github.com/stanfordnlp/CoreNLP): Natural Language Processing | Natural Language Processing
82) [Cortex](https://github.com/cortexlabs/cortex): Machine Learning | Platform
83) [CouchDB](https://github.com/apache/couchdb): Data | Relational DB
84) [Couler](https://github.com/couler-proj/couler): Model | Workflow
85) [Cyclone](https://github.com/caicloud/cyclone): Model | Workflow
86) [D3 (Data-Driven Documents)](https://github.com/d3/d3): Data | Visualization
87) [d6tflow](https://github.com/d6t/d6tflow): Model | Workflow
88) [DAGSTER](https://github.com/dagster-io/dagster): Data | Pipeline Management
89) [dash](https://github.com/plotly/dash): Data | Visualization
90) [Dask](https://github.com/dask/dask): Programming | Programming
91) [Data Prep Kit](https://github.com/data-prep-kit/data-prep-kit): Machine Learning | Framework
92) [DataHub](https://github.com/datahub-project/datahub): Data | Operations
93) [Datashim](https://github.com/datashim-io/datashim): Data | Operations
94) [DAWNBench](https://github.com/stanford-futuredata/dawn-bench-entries): Model | Benchmarking
95) [deck.gl](https://github.com/visgl/deck.gl): Data | Visualization
96) [DeepCausality](https://github.com/deepcausality-rs/deep_causality): Machine Learning | Library
97) [DeepDetect](https://github.com/jolibrain/deepdetect): Deep Learning | Platform
98) [DeepLIFT](https://github.com/kundajelab/deeplift): Trusted & Responsible AI | Bias & Fairness
99) [DeepMind Lab](https://github.com/deepmind/lab): Reinforcement Learning | Reinforcement Learning
100) [DeepRec](https://github.com/alibaba/DeepRec): Deep Learning | Framework
101) [DeepSpeech](https://github.com/mozilla/DeepSpeech): Natural Language Processing | Natural Language Processing
102) [DELTA](https://github.com/Delta-ML/delta): Natural Language Processing | Natural Language Processing
103) [Delta Lake](https://github.com/delta-io/delta): Data | Store & Format
104) [Determined AI](https://github.com/determined-ai/determined): Deep Learning | Platform
105) [Differential Privacy Library](https://github.com/google/differential-privacy): Security & Privacy | Security & Privacy
106) [dlrm](https://github.com/facebookresearch/dlrm): Model | Tool
107) [DLRover](https://github.com/intelligent-machine-learning/dlrover): Model | Training
108) [DocArray](https://github.com/docarray/docarray): Data | Store & Format
109) [doccano](https://github.com/doccano/doccano): Data | Labeling & Annotation
110) [Docling](https://github.com/docling-project/docling): Data | Store & Format
111) [Dopamine](https://github.com/google/dopamine): Reinforcement Learning | Reinforcement Learning
112) [dotmesh](https://github.com/dotmesh-io/dotmesh): Data | Versioning
113) [Dragonfly](https://github.com/dragonflyoss/Dragonfly2): Data | Store & Format
114) [Druid](https://github.com/apache/druid): Data | Store & Format
115) [DVC](https://github.com/iterative/dvc): Data | Versioning
116) [Dynamic Neural Network Toolkit](https://github.com/clab/dynet): Deep Learning | Framework
117) [ecco](https://github.com/jalammar/ecco): Data | Visualization
118) [Eclipse Deeplearning4j](https://github.com/eclipse/deeplearning4j): Deep Learning | Library
119) [Egeria](https://github.com/odpi/egeria): Data | Governance
120) [Elastic Deep Learning (EDL)](https://github.com/elasticdeeplearning/edl): Distributed Computing | Computing & Management
121) [ELI5](https://github.com/TeamHG-Memex/eli5): Trusted & Responsible AI | Explainability
122) [Elyra](https://github.com/elyra-ai/elyra): Notebook Environment | Notebook Environment
123) [Embedded Learning Library](https://github.com/Microsoft/ELL): Model | Training
124) [envd](https://github.com/tensorchord/envd): Notebook Environment | Notebook Environment
125) [euler](https://github.com/alibaba/euler): Deep Learning | Framework
126) [Facets](https://github.com/PAIR-code/facets): Data | Visualization
127) [Fainlearn](https://github.com/fairlearn/fairlearn): Trusted & Responsible AI | Bias & Fairness
128) [fast.ai](https://github.com/fastai/fastai): Deep Learning | Library
129) [fastText](https://github.com/facebookresearch/fastText): Natural Language Processing | Natural Language Processing
130) [FastTrackML](https://github.com/G-Research/fasttrackml): Data | Versioning
131) [FATE](https://github.com/FederatedAI/FATE): Model | Federated Learning
132) [faust](https://github.com/robinhood/faust): Data | Stream Processing
133) [Feast](https://github.com/feast-dev/feast): Data | Feature Engineering
134) [Feathr](https://github.com/linkedin/feathr): Data | Feature Engineering
135) [Featuretools](https://github.com/alteryx/featuretools): Data | Feature Engineering
136) [FlagAI](https://github.com/BAAI-Open/FlagAI): Model | Tool
137) [Flair](https://github.com/flairNLP/flair): Natural Language Processing | Natural Language Processing
138) [FLAML](https://github.com/microsoft/FLAML): Model | Tool
139) [Flashlight](https://github.com/flashlight/flashlight): Machine Learning | Library
140) [Flink](https://github.com/apache/flink): Data | Stream Processing
141) [Fluentd](https://github.com/fluent/fluentd): Data | Stream Processing
142) [Flyte](https://github.com/flyteorg/flyte): Model | Workflow
143) [Foolbox](https://github.com/bethgelab/foolbox): Trusted & Responsible AI | Adversarial
144) [ForestFlow](https://github.com/ForestFlow/ForestFlow): Machine Learning | Platform
145) [Generic Neural Elastic Search (GNES)](https://github.com/gnes-ai/gnes): Distributed Computing | Computing & Management
146) [genie](https://github.com/Netflix/genie): Distributed Computing | Computing & Management
147) [Gluon-NLP](https://github.com/dmlc/gluon-nlp): Natural Language Processing | Natural Language Processing
148) [Grafana](https://github.com/grafana/grafana): Data | Visualization
149) [GraphScope](https://github.com/alibaba/graphscope): Distributed Computing | Computing & Management
150) [Gravitino](https://github.com/apache/gravitino): Data | Governance
151) [great_expectations](https://github.com/great-expectations/great_expectations): Data | Operations
152) [H2o.ai](https://github.com/h2oai/h2o-3): Machine Learning | Platform
153) [Hawq](https://github.com/apache/hawq): Data | SQL Engine
154) [Haystack](https://github.com/deepset-ai/haystack): Natural Language Processing | Natural Language Processing
155) [HE Lib](https://github.com/homenc/HElib): Security & Privacy | Security & Privacy
156) [Horizon](https://github.com/facebookresearch/ReAgent): Reinforcement Learning | Reinforcement Learning
157) [Horovod](https://github.com/horovod/horovod): Model | Training
158) [Hudi](https://github.com/apache/hudi): Data | Store & Format
159) [HugeGraph](https://github.com/apache/incubator-hugegraph): Data | Store & Format
160) [HyperOpt](https://github.com/hyperopt/hyperopt): Model | Parameter
161) [Infer.net](https://github.com/dotnet/infer): Programming | Programming
162) [InfluxDB](https://github.com/influxdata/influxdb): Data | Store & Format
163) [InterpretML](https://github.com/interpretml/interpret): Trusted & Responsible AI | Explainability
164) [IPython](https://github.com/ipython/ipython): Notebook Environment | Notebook Environment
165) [IREE](https://github.com/iree-org/iree): Machine Learning | Library
166) [JanusGraph](https://github.com/JanusGraph/janusgraph): Data | Store & Format
167) [Julia](https://github.com/JuliaLang/julia): Programming | Programming
168) [Jupyter Notebooks](https://github.com/jupyter/notebook): Notebook Environment | Notebook Environment
169) [Kafka](https://github.com/apache/kafka): Data | Stream Processing
170) [Kashgari](https://github.com/BrikerMan/Kashgari): Natural Language Processing | Natural Language Processing
171) [Katib](https://github.com/kubeflow/katib): Model | Parameter
172) [Kedro](https://github.com/kedro-org/kedro): Model | Workflow
173) [Keras](https://github.com/keras-team/keras): Deep Learning | Library
174) [Kestra](https://github.com/kestra-io/kestra): Model | Workflow
175) [Kompute](https://github.com/KomputeProject/kompute): Programming | Programming
176) [KServe](https://github.com/kserve/kserve): Machine Learning | Platform
177) [Kubeflow](https://github.com/kubeflow/kubeflow): Machine Learning | Platform
178) [Kubernetes](https://github.com/kubernetes/kubernetes): Distributed Computing | Computing & Management
179) [Label Studio](https://github.com/heartexlabs/label-studio): Data | Labeling & Annotation
180) [Labelbox](https://github.com/Labelbox/Labelbox): Data | Labeling & Annotation
181) [LabelImg](https://github.com/tzutalin/labelImg): Data | Labeling & Annotation
182) [LakeSoul](https://github.com/meta-soul/LakeSoul): Data | Store & Format
183) [Langchain](https://github.com/langchain-ai/langchain): Generative AI | Tools
184) [LASER](https://github.com/facebookresearch/LASER): Natural Language Processing | Natural Language Processing
185) [LightGBM](https://github.com/Microsoft/LightGBM): Machine Learning | Framework
186) [LIME](https://github.com/marcotcr/lime): Trusted & Responsible AI | Explainability
187) [Livy](https://github.com/apache/incubator-livy): Distributed Computing | Interface
188) [Logstash](https://github.com/elastic/logstash): Data | Stream Processing
189) [Lucene](https://github.com/apache/lucene-solr): Natural Language Processing | Natural Language Processing
190) [Lucid](https://github.com/tensorflow/lucid): Trusted & Responsible AI | Explainability
191) [Ludwig](https://github.com/ludwig-ai/ludwig): Model | Training
192) [Luigi](https://github.com/spotify/luigi): Model | Workflow
193) [Machine Learning eXchange (MLX)](https://github.com/machine-learning-exchange/mlx): Model | Marketplace
194) [Mahout](https://github.com/apache/mahout): Machine Learning | Framework
195) [Marquez](https://github.com/MarquezProject/marquez): Data | Operations
196) [MARS](https://github.com/mars-project/mars): Programming | Programming
197) [Mathesar](https://github.com/centerofci/mathesar): Data | Operations
198) [MediaPipe](https://github.com/google/mediapipe): Machine Learning | Library
199) [Metabase](https://github.com/metabase/metabase): Data | Visualization
200) [Metaflow](https://github.com/Netflix/metaflow): Machine Learning | Platform
201) [Milvus](https://github.com/milvus-io/milvus): Data | Store & Format
202) [MindMeld](https://github.com/cisco/mindmeld): Natural Language Processing | Natural Language Processing
203) [MindSpore](https://github.com/mindspore-ai/mindspore): Deep Learning | Framework
204) [ML.net](https://github.com/dotnet/machinelearning): Machine Learning | Framework
205) [mleap](https://github.com/combust/mleap): Model | Workflow
206) [MLFlow](https://github.com/mlflow/mlflow): Machine Learning | Platform
207) [mlpack](https://github.com/mlpack/mlpack): Machine Learning | Library
208) [MLPerf](https://github.com/mlcommons/training): Model | Benchmarking
209) [MMdnn](https://github.com/Microsoft/MMdnn): Model | Tool
210) [MNN](https://github.com/alibaba/MNN): Model | Inference
211) [Model Asset eXchange (MAX)](https://github.com/IBM/MAX-Base): Model | Marketplace
212) [Model Server for Apache MXNet](https://github.com/awslabs/multi-model-server): Model | Tool
213) [ModelDB](https://github.com/VertaAI/modeldb): Model | Tool
214) [Monocle](https://github.com/monocle2ai/monocle): Generative AI | Tools
215) [MXNet](https://github.com/apache/incubator-mxnet): Deep Learning | Framework
216) [MySQL](https://github.com/mysql/mysql-server): Data | Relational DB
217) [Nauta](https://github.com/IntelAI/Nauta): Distributed Computing | Computing & Management
218) [ncnn](https://github.com/Tencent/ncnn): Deep Learning | Framework
219) [Neo-AI](https://github.com/neo-ai/neo-ai-dlr): Model | Tool
220) [Netron](https://github.com/lutzroeder/netron): Model | Tool
221) [Neural Network Distiller](https://github.com/IntelLabs/distiller): Deep Learning | Tool
222) [Neural Network Libraries](https://github.com/sony/nnabla): Deep Learning | Library
223) [Neuropod](https://github.com/uber/neuropod): Model | Format & Interface
224) [Nilearn](https://github.com/nilearn/nilearn): Machine Learning | Library
225) [NLP Architect](https://github.com/IntelLabs/nlp-architect): Natural Language Processing | Natural Language Processing
226) [NNStreamer](https://github.com/nnstreamer/nnstreamer): Data | Stream Processing
227) [Numba](https://github.com/numba/numba): Programming | Programming
228) [NumPy](https://github.com/numpy/numpy): Programming | Programming
229) [Nyoka](https://github.com/SoftwareAG/nyoka): Programming | Programming
230) [OAAX](https://github.com/OAAX-standard): Machine Learning | Framework
231) [Onepanel](https://github.com/onepanelio/onepanel): Deep Learning | Platform
232) [ONNX](https://github.com/onnx/onnx): Model | Format & Interface
233) [ONNX Runtime](https://github.com/microsoft/onnxruntime): Model | Tool
234) [Open Model Initiative](https://github.com/Open-Model-Initiative/OMI-Model-Standards): Generative AI | Models
235) [Open Platform for Enterprise AI (OPEA)](https://github.com/opea-project/GenAIExamples): Machine Learning | Platform
236) [Open Voice Interoperability Initiative](https://github.com/open-voice-interoperability): Distributed Computing | Interface
237) [Open Voice Network TrustMark](https://github.com/Open-Voice-Trustmark/docs): Trusted & Responsible AI | Bias & Fairness
238) [OpenAI Gym](https://github.com/openai/gym): Reinforcement Learning | Reinforcement Learning
239) [OpenBytes](https://github.com/Project-OpenBytes/OpenBytes): Data | Lineage
240) [OpenCV](https://github.com/opencv/opencv): Machine Learning | Library
241) [OpenDataology](https://github.com/OpenDataology/OpenDataology): Data | Lineage
242) [OpenDS4All](https://github.com/odpi/OpenDS4All): Data | Education
243) [OpenFL](https://github.com/intel/openfl): Model | Federated Learning
244) [OpenLineage](https://github.com/OpenLineage/OpenLineage): Data | Lineage
245) [OpenMLDB](https://github.com/4paradigm/OpenMLDB): Data | Feature Engineering
246) [OpenNLP](https://github.com/apache/opennlp): Natural Language Processing | Natural Language Processing
247) [OpenNN](https://github.com/Artelnics/OpenNN): Machine Learning | Library
248) [OpenShift](https://github.com/openshift/origin): Distributed Computing | Computing & Management
249) [Orchest](https://github.com/orchest/orchest): Model | Workflow
250) [PaddlePaddle](https://github.com/PaddlePaddle/Paddle): Deep Learning | Framework
251) [pandas](https://github.com/pandas-dev/pandas): Data | Store & Format
252) [ParlAI](https://github.com/facebookresearch/ParlAI): Natural Language Processing | Natural Language Processing
253) [Parquet](https://github.com/apache/parquet-format): Data | Store & Format
254) [Petastorm](https://github.com/uber/petastorm): Model | Training
255) [PiFlow](https://github.com/cas-bigdatalab/piflow): Data | Pipeline Management
256) [Pilosa](https://github.com/pilosa/pilosa): Data | Store & Format
257) [Pipeline.ai](https://github.com/PipelineAI/pipeline): Model | Tool
258) [PixieDust](https://github.com/pixiedust/pixiedust): Notebook Environment | Notebook Environment
259) [Plaid ML](https://github.com/plaidml/plaidml): Deep Learning | Tool
260) [PlaNet](https://github.com/google-research/planet): Reinforcement Learning | Reinforcement Learning
261) [Polyaxon](https://github.com/polyaxon/polyaxon): Deep Learning | Platform
262) [Polynote](https://github.com/polynote/polynote): Notebook Environment | Notebook Environment
263) [Pomegranete](https://github.com/jmschrei/pomegranate): Programming | Programming
264) [Postgres](https://github.com/postgres/postgres): Data | Relational DB
265) [Pravega](https://github.com/pravega/pravega): Data | Stream Processing
266) [PredictionIO](https://github.com/apache/predictionio): Machine Learning | Platform
267) [PREFECT](https://github.com/PrefectHQ/prefect): Data | Stream Processing
268) [Prefect](https://github.com/prefecthq/prefect): Model | Workflow
269) [Presto](https://github.com/prestodb/presto): Data | SQL Engine
270) [Prometheus](https://github.com/prometheus/prometheus): Data | Visualization
271) [Pulsar](https://github.com/apache/pulsar): Data | Stream Processing
272) [PyCaret](https://github.com/pycaret/pycaret): Machine Learning | Library
273) [PyMC3](https://github.com/pymc-devs/pymc): Programming | Programming
274) [Pyro](https://github.com/pyro-ppl/pyro): Programming | Programming
275) [PySyft](https://github.com/OpenMined/PySyft): Model | Federated Learning
276) [PyText](https://github.com/facebookresearch/pytext): Natural Language Processing | Natural Language Processing
277) [Pythia](https://github.com/facebookresearch/mmf): Deep Learning | Framework
278) [Python](https://github.com/python/cpython): Programming | Programming
279) [PyTorch](https://github.com/pytorch/pytorch): Deep Learning | Framework
280) [PyTorch BigGraph](https://github.com/facebookresearch/PyTorch-BigGraph): Deep Learning | Tool
281) [PyTorch Geometric](https://github.com/pyg-team/pytorch_geometric): Deep Learning | Tool
282) [PyTorch Ignite](https://github.com/pytorch/ignite): Deep Learning | Library
283) [PyTorch Lightning](https://github.com/PyTorchLightning/pytorch-lightning): Deep Learning | Library
284) [PyTorchVideo](https://github.com/facebookresearch/pytorchvideo): Deep Learning | Library
285) [Quilt Data](https://github.com/quiltdata/quilt): Data | Versioning
286) [RASA NLU](https://github.com/RasaHQ/rasa): Natural Language Processing | Natural Language Processing
287) [Ray](https://github.com/ray-project/ray): Machine Learning | Framework
288) [RCloud](https://github.com/att/rcloud): Data | Visualization
289) [Recommenders](https://github.com/microsoft/recommenders): Machine Learning | Library
290) [redash](https://github.com/getredash/redash): Data | Visualization
291) [rmarkdown](https://github.com/rstudio/rmarkdown): Notebook Environment | Notebook Environment
292) [RStudio IDE](https://github.com/rstudio/rstudio): Programming | Programming
293) [RWKV](https://github.com/RWKV/RWKV-infctx-trainer): Generative AI | Models
294) [Ryoma](https://github.com/project-ryoma/ryoma): Deep Learning | Framework
295) [Samza](https://github.com/apache/samza): Data | Stream Processing
296) [SapientML](https://github.com/sapientml/sapientml): Machine Learning | Library
297) [SciKit-learn](https://github.com/scikit-learn/scikit-learn): Machine Learning | Library
298) [SciPy](https://github.com/scipy/scipy): Programming | Programming
299) [seaborn](https://github.com/mwaskom/seaborn): Data | Visualization
300) [SEAL](https://github.com/microsoft/SEAL): Security & Privacy | Security & Privacy
301) [SEED RL](https://github.com/google-research/seed_rl): Reinforcement Learning | Reinforcement Learning
302) [Seldon](https://github.com/SeldonIO/seldon-core): Machine Learning | Platform
303) [Semantic Kernel](https://github.com/microsoft/semantic-kernel): Model | Format & Interface
304) [Semantic Segmentation Editor](https://github.com/Hitachi-Automotive-And-Industry-Lab/semantic-segmentation-editor): Data | Labeling & Annotation
305) [ShaderNN](https://github.com/inferenceengine/shadernn): Deep Learning | Framework
306) [SHAP](https://github.com/slundberg/shap): Trusted & Responsible AI | Explainability
307) [Shogun](https://github.com/shogun-toolbox/shogun): Machine Learning | Library
308) [Singularity](https://github.com/apptainer/singularity): Distributed Computing | Computing & Management
309) [Skater](https://github.com/oracle/Skater): Trusted & Responsible AI | Explainability
310) [SKIP Language](https://github.com/skiplang/skip): Programming | Programming
311) [snorkel](https://github.com/snorkel-team/snorkel): Data | Operations
312) [SOAJS](https://github.com/soajs/soajs): Distributed Computing | Computing & Management
313) [Sonnet](https://github.com/deepmind/Sonnet): Machine Learning | Library
314) [spaCy](https://github.com/explosion/spaCy): Natural Language Processing | Natural Language Processing
315) [Spark-NLP](https://github.com/JohnSnowLabs/spark-nlp): Natural Language Processing | Natural Language Processing
316) [sparklyr](https://github.com/sparklyr/sparklyr): Distributed Computing | Interface
317) [SQLFlow](https://github.com/sql-machine-learning/sqlflow): Data | SQL Engine
318) [Stable Baselines](https://github.com/hill-a/stable-baselines): Reinforcement Learning | Reinforcement Learning
319) [Stan](https://github.com/stan-dev/stan): Programming | Programming
320) [StarRocks](https://github.com/StarRocks/starrocks): Data | Store & Format
321) [Stencila](https://github.com/stencila/stencila): Notebook Environment | Notebook Environment
322) [Streamlit](https://github.com/streamlit/streamlit): Notebook Environment | Notebook Environment
323) [studio.ml](https://github.com/studioml/studio): Model | Tool
324) [Substra](https://github.com/Substra/substra): Model | Federated Learning
325) [Superset](https://github.com/apache/superset): Data | Visualization
326) [talos](https://github.com/autonomio/talos): Model | Parameter
327) [Tekton Pipelines](https://github.com/tektoncd/pipeline): Data | Pipeline Management
328) [TensorBoard](https://github.com/tensorflow/tensorboard): Data | Visualization
329) [Tensorflow](https://github.com/tensorflow/tensorflow): Deep Learning | Framework
330) [TensorFlow Federated](https://github.com/tensorflow/federated): Model | Federated Learning
331) [TensorFlow Model Analysis](https://github.com/tensorflow/model-analysis): Model | Tool
332) [TensorFlow Privacy](https://github.com/tensorflow/privacy): Security & Privacy | Security & Privacy
333) [TensorRT](https://github.com/NVIDIA/TensorRT): Model | Inference
334) [TensorRT Inference Server](https://github.com/triton-inference-server/server): Model | Inference
335) [Text Generation Inference](https://github.com/huggingface/text-generation-inference): Model | Inference
336) [TF Encrypted](https://github.com/tf-encrypted/tf-encrypted): Security & Privacy | Security & Privacy
337) [TiKV](https://github.com/tikv/tikv): Data | Relational DB
338) [TorchRec](https://github.com/pytorch/torchrec): Model | Training
339) [TorchServe](https://github.com/pytorch/serve): Model | Tool
340) [TPOT](https://github.com/EpistasisLab/tpot): Data | Pipeline Management
341) [TRAINS](https://github.com/allegroai/clearml): Model | Workflow
342) [Transformers](https://github.com/huggingface/transformers): Natural Language Processing | Natural Language Processing
343) [TransmogrifAI](https://github.com/salesforce/TransmogrifAI): Machine Learning | Library
344) [TreeInterpreter](https://github.com/andosa/treeinterpreter): Trusted & Responsible AI | Explainability
345) [Trino](https://github.com/trinodb/trino): Data | SQL Engine
346) [TruLens](https://github.com/truera/trulens): Generative AI | Tools
347) [tsfresh](https://github.com/blue-yonder/tsfresh): Data | Feature Engineering
348) [Turi Create](https://github.com/apple/turicreate): Model | Tool
349) [TVM](https://github.com/apache/tvm): Deep Learning | Tool
350) [Unity Catalog](https://github.com/unitycatalog/unitycatalog): Data | Governance
351) [uReplicator](https://github.com/uber/uReplicator): Data | Stream Processing
352) [uTensor](https://github.com/uTensor/uTensor): Model | Inference
353) [Vald](https://github.com/vdaas/vald): Data | Store & Format
354) [VEARCH](https://github.com/vearch/vearch): Data | Store & Format
355) [Vespa](https://github.com/vespa-engine/vespa): Data | Store & Format
356) [Vineyard](https://github.com/v6d-io/v6d): Data | Store & Format
357) [Visual Object Tagging Tool (VoTT)](https://github.com/Microsoft/VoTT): Data | Labeling & Annotation
358) [Volcano](https://github.com/volcano-sh/volcano): Model | Workflow
359) [Vortex](https://github.com/vortex-data): Data | Store & Format
360) [Vowpal Wabbit](https://github.com/VowpalWabbit/vowpal_wabbit): Machine Learning | Platform
361) [whylogs](https://github.com/whylabs/whylogs): Data | Operations
362) [X-DeepLearning](https://github.com/alibaba/x-deeplearning): Deep Learning | Platform
363) [XGBoost](https://github.com/dmlc/xgboost): Machine Learning | Library
364) [xLearn](https://github.com/aksnzhy/xlearn): Machine Learning | Library
365) [XLM](https://github.com/facebookresearch/XLM): Natural Language Processing | Natural Language Processing
366) [YouTokenToMe](https://github.com/VKCOM/YouTokenToMe): Natural Language Processing | Natural Language Processing
367) [ZenML](https://github.com/zenml-io/zenml): Machine Learning | Framework

---

**Document Version**: 2.4  
**Last Reviewed**: June 2026
