import unittest
import random
import numpy
import keras
from keras_self_attention import Attention


class TestLocal(unittest.TestCase):

    def check_local_range(self, attention_type):
        sentences = [
            ['All', 'work', 'and', 'no', 'play'],
            ['makes', 'Jack', 'a', 'dull', 'boy', '.'],
            ['From', 'that', 'day', 'forth', 'my', 'arm', 'changed'],
        ]
        token_dict = {
            '': 0,
            '<UNK>': 1,
        }
        sentence_len = max(map(len, sentences))
        input_data = [[0] * sentence_len for _ in range(len(sentences))]
        for i, sentence in enumerate(sentences):
            for j, token in enumerate(sentence):
                if token in token_dict:
                    input_data[i][j] = token_dict[token]
                elif random.randint(0, 5) == 0:
                    input_data[i][j] = token_dict['<UNK>']
                else:
                    input_data[i][j] = len(token_dict)
                    token_dict[token] = len(token_dict)
        input_data = numpy.asarray(input_data)
        inputs = keras.layers.Input(shape=(None,))
        embd = keras.layers.Embedding(input_dim=len(token_dict),
                                      output_dim=16,
                                      mask_zero=True)(inputs)
        lstm = keras.layers.Bidirectional(keras.layers.LSTM(units=16,
                                                            return_sequences=True))(embd)
        att, weights = Attention(return_attention=True,
                                 attention_width=5,
                                 attention_type=attention_type,
                                 kernel_regularizer=keras.regularizers.l2(1e-4),
                                 bias_regularizer=keras.regularizers.l1(1e-4))(lstm)
        dense = keras.layers.Dense(units=5)(att)
        model = keras.models.Model(inputs=inputs, outputs=[dense, weights])
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            loss_weights=[1.0, 0.0],
            metrics=['categorical_accuracy'],
        )
        model.summary(line_length=100)
        outputs = model.predict(input_data)
        attention = outputs[1]
        for i, sentence in enumerate(sentences):
            for j in range(sentence_len):
                for k in range(sentence_len):
                    if j < len(sentence) and k < len(sentence) and abs(j - k) <= 2:
                        self.assertGreater(attention[i][j][k], 0.0)
                    else:
                        self.assertEqual(attention[i][j][k], 0.0)
                if j < len(sentence):
                    self.assertTrue(abs(numpy.sum(attention[i][j]) - 1.0) < 1e-6)

    def test_add(self):
        self.check_local_range(attention_type=Attention.ATTENTION_TYPE_ADD)

    def test_mul(self):
        self.check_local_range(attention_type=Attention.ATTENTION_TYPE_MUL)

    def test_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            inputs = keras.layers.Input(shape=(None,))
            embd = keras.layers.Embedding(input_dim=30,
                                          output_dim=16,
                                          mask_zero=True)(inputs)
            lstm = keras.layers.Bidirectional(keras.layers.LSTM(units=16,
                                                                return_sequences=True))(embd)
            att = Attention(attention_width=15)
            att._backend = 'random'
            att = att(lstm)
            dense = keras.layers.Dense(units=5)(att)
            model = keras.models.Model(inputs=inputs, outputs=dense)
            model.compile(
                optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['categorical_accuracy'],
            )
