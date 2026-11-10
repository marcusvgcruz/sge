"""Testes do signal de saída do SGE.

Cobrem o bug em que o signal chamava `notify.send_event()` (inexistente) e
engolia a exceção com `except: pass` — o aviso saía em silêncio.
"""
from django.test import TestCase
from categories.models import Category
from brands.models import Brand
from products.models import Product
from outflows.models import Outflow
import outflows.signals as signals_mod
from services.notify import Notify


class SendOutflowEventSignalTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Vestuário')
        self.brand = Brand.objects.create(name='Marca Teste')
        self.product = Product.objects.create(
            title='Camisa Polo M',
            category=self.category,
            brand=self.brand,
            cost_price=39.90,
            selling_price=89.90,
            quantity=10,
        )

    def test_signal_chama_send_order_event_com_payload_correto(self):
        """O signal deve chamar send_order_event (o método que existe no Notify)."""
        chamadas = []

        def fake_send_order_event(self, data):
            chamadas.append(data)

        original = Notify.send_order_event
        Notify.send_order_event = fake_send_order_event
        try:
            Outflow.objects.create(
                product=self.product,
                quantity=2,
                description='Venda no balcão',
            )
        finally:
            Notify.send_order_event = original

        self.assertEqual(len(chamadas), 1, 'send_order_event deveria ser chamado 1x')
        payload = chamadas[0]
        self.assertEqual(payload['event_type'], 'create_outflow')
        self.assertEqual(payload['product'], 'Camisa Polo M')
        self.assertEqual(payload['quantity'], 2)
        self.assertEqual(payload['product_cost_price'], 39.9)
        self.assertEqual(payload['product_selling_price'], 89.9)
        self.assertEqual(payload['description'], 'Venda no balcão')
        self.assertIn('timestamp', payload)

    def test_signal_nao_chama_metodo_inexistente_send_event(self):
        """Regressão: o signal não deve mais referenciar send_event."""
        self.assertFalse(
            hasattr(Notify, 'send_event'),
            'Notify não define send_event — o signal não pode chamá-lo',
        )
        import inspect
        src = inspect.getsource(signals_mod.send_outflow_event)
        self.assertNotIn('send_event(', src.replace('send_order_event(', ''))
        self.assertIn('send_order_event(', src)

    def test_falha_no_notify_e_logada_nao_engolida(self):
        """Se o Notify falhar, a exceção deve ser logada (não pass silencioso)."""
        def fake_send_order_event(self, data):
            raise ConnectionError('notify fora do ar')

        original = Notify.send_order_event
        Notify.send_order_event = fake_send_order_event
        try:
            with self.assertLogs('outflows.signals', level='ERROR') as logs:
                Outflow.objects.create(
                    product=self.product,
                    quantity=1,
                    description='Venda com notify quebrado',
                )
        finally:
            Notify.send_order_event = original

        self.assertEqual(len(logs.output), 1)
        self.assertIn('Falha ao enviar evento de saída para o Notify', logs.output[0])
        self.assertIn('ConnectionError', logs.output[0])

    def test_excecao_nao_interrompe_o_registro_da_saida(self):
        """Mesmo com falha no envio, a saída deve ficar registrada no banco."""
        def fake_send_order_event(self, data):
            raise RuntimeError('boom')

        original = Notify.send_order_event
        Notify.send_order_event = fake_send_order_event
        try:
            outflow = Outflow.objects.create(
                product=self.product,
                quantity=3,
                description='Venda',
            )
        finally:
            Notify.send_order_event = original

        self.assertTrue(
            Outflow.objects.filter(pk=outflow.pk).exists(),
            'a saída deveria persistir mesmo com falha no envio',
        )
