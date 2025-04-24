import logging

txlist=[]	# Liste zu sendender Botschaften

def add2stack(topic, request):
    txlist.append(topic)
    txlist.append(request)
    
def tx(client):
    if len(txlist)>1:
        topic = txlist.pop(0)
        request = txlist.pop(0)
        logging.info(f'Sende an Topic {topic} die Anforderung {request}')
        client.publish(topic,request)
