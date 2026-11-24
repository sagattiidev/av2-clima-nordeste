"""
Producer — busca o dia mais recente de cada cidade na Open-Meteo e publica no
tópico Kafka. Roda como job agendado (ver .github/workflows/kafka-produce.yml)
ou manualmente: `python producer.py`.

Não escreve no Postgres — essa é a responsabilidade do consumer.py, que
assina o mesmo tópico. O producer só materializa o evento "novo dado
disponível" no Kafka.
"""

import json
import sys

import clima_client as clima
import kafka_common


def build_event(city_key, dia):
    """Evento publicado: uma cidade, um dia, todas as variáveis daquele dia."""
    return {
        "city": city_key,
        "ref_date": dia["ref_date"].isoformat(),
        "values": dia["values"],
    }


def main():
    producer = kafka_common.get_producer()
    published = 0

    for city_key in clima.CIDADES:
        try:
            # Só o dia mais recente — o histórico completo já foi semeado
            # pelo cache em lote do app.py na primeira execução.
            dias = clima.fetch_city(city_key, days=1)
        except Exception as exc:  # noqa: BLE001
            print(f"[producer] falha ao buscar {city_key}: {exc}", file=sys.stderr)
            continue

        for dia in dias:
            event = build_event(city_key, dia)
            producer.send(kafka_common.TOPIC, key=city_key, value=json.dumps(event))
            published += 1
            print(f"[producer] publicado: {event}")

    producer.flush(timeout=10)
    producer.close()
    print(f"[producer] concluído — {published} evento(s) publicado(s)")


if __name__ == "__main__":
    main()
