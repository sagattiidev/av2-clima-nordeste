"""
Consumer — assina o tópico Kafka e grava cada evento na tabela clima_diario
do Postgres (a mesma que o dashboard lê). Dois modos de uso:

  Contínuo (para rodar como Background Worker no Render):
      python consumer.py

  Em lote, com timeout (para rodar como job agendado no GitHub Actions —
  ver .github/workflows/kafka-consume-batch.yml):
      python consumer.py --once --timeout 30

Como os dois processos usam o MESMO group_id (KAFKA_GROUP_ID, default
"clima-consumer"), o Kafka nunca entrega a mesma mensagem para ambos ao
mesmo tempo — o job em lote funciona como rede de segurança para quando
o worker contínuo estiver fora do ar, sem duplicar processamento.
"""

import argparse
import datetime
import json
import sys
import time

import clima_client as clima
import kafka_common


def handle_message(msg) -> None:
    event = json.loads(msg.value)
    city_key = event["city"]
    if city_key not in clima.CIDADES:
        print(f"[consumer] cidade desconhecida ignorada: {city_key}", file=sys.stderr)
        return

    values = {
        var: float(value)
        for var, value in event["values"].items()
        if var in clima.VARIAVEIS and value is not None
    }
    dia = {"ref_date": datetime.date.fromisoformat(event["ref_date"]), "values": values}
    gravados = clima.upsert_days(city_key, [dia])
    print(f"[consumer] gravado: cidade={city_key} data={dia['ref_date']} registros={gravados}")


def run_once(timeout_seconds: int) -> None:
    consumer = kafka_common.get_consumer()
    deadline = time.time() + timeout_seconds
    count = 0
    try:
        while time.time() < deadline:
            batch = consumer.poll(timeout_ms=2000, max_records=50)
            if not batch:
                continue
            for records in batch.values():
                for msg in records:
                    handle_message(msg)
                    count += 1
    finally:
        consumer.close()
    print(f"[consumer] modo lote concluído — {count} evento(s) processado(s)")


def run_forever() -> None:
    consumer = kafka_common.get_consumer()
    print("[consumer] aguardando eventos continuamente... (Ctrl+C para sair)")
    try:
        for msg in consumer:
            handle_message(msg)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="processa por um período fixo e sai")
    parser.add_argument("--timeout", type=int, default=30, help="segundos no modo --once")
    args = parser.parse_args()

    clima.init_db()

    if args.once:
        run_once(args.timeout)
    else:
        run_forever()


if __name__ == "__main__":
    main()
