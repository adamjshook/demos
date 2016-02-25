import rpyc
from rpyc.utils.server import ThreadedServer
import sys
import json
import logging
from StringIO import StringIO
import avro.schema
from avro.io import DatumWriter
from avro.io import AvroTypeException
from kafka import KafkaProducer
from avro.io import BinaryEncoder

schema = avro.schema.parse(open("match.avsc").read())

def __init_logging():
    root = logging.getLogger()
    root.setLevel(logging.getLevelName("INFO"))
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root.addHandler(ch)

class LolMatchData(rpyc.Service):

    _topic = None
    _producer = None

    def exposed_match(self, dataStr):
        try:
            data = json.loads(dataStr)

            avroObject = { }
            avroObject["mapId"] = data["mapId"]
            avroObject["matchCreation"] = data["matchId"]
            avroObject["matchDuration"] = data["matchDuration"]
            avroObject["matchId"] = data["matchId"]
            avroObject["matchMode"] = data["matchMode"]
            avroObject["winningTeam"] = data["teams"][0]["teamId"] if data["teams"][0]["winner"] else data["teams"][1]["teamId"]
            avroObject["participants"] = []
            avroObject["teams"] = []

            for pData in data["participants"]:
                p = { }
                p["championId"] = pData["championId"]
                p["teamId"] = pData["teamId"]
                p["winner"] = pData["teamId"] == avroObject["winningTeam"]

                pId = pData["participantId"]
                for pIdData in data["participantIdentities"]:
                    if pIdData["participantId"] == pId:
                        p["summonerId"] = pIdData["player"]["summonerId"]
                        p["summonerName"] = pIdData["player"]["summonerName"]
                        break

                avroObject["participants"].append(p)

            for tData in data["teams"]:
                t = { }
                t["teamId"] = tData["teamId"]
                t["winner"] = tData["winner"]
                t["firstInhibitor"] = tData["firstInhibitor"]
                t["firstBlood"] = tData["firstBlood"]
                t["firstTower"] = tData["firstTower"]

                avroObject["teams"].append(t)

            stream = StringIO()
            writer = DatumWriter(writers_schema=schema)
            encoder = BinaryEncoder(stream)
            writer.write(avroObject, encoder)
            self._producer.send(self._topic, stream.getvalue())
            self._producer.flush()

            print "Wrote %s" % avroObject

        except AvroTypeException as e:
            print e
        except ValueError as e:
            print e
        except TypeError as e:
            print e
        except KeyError as e:
            print e
        except:
            print str(sys.exc_info()[0])

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "usage: python producer.py <server.port> <brokers> <topic>"
        print "    server.port - port to bind to for rpyc calls"
        print "    brokers - comma-delimited list of host:port pairs for Kafka brokers"
        print "    topic - Kafka topic to post messages to, must exist"
        sys.exit(1)

    __init_logging()

    port = int(sys.argv[1])
    brokers = sys.argv[2]
    topic = sys.argv[3]

    LolMatchData._producer = KafkaProducer(bootstrap_servers=brokers)
    LolMatchData._topic = topic

    ThreadedServer(LolMatchData, port=port).start()
