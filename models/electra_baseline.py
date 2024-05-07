from transformers import ElectraModel, BertModel, DebertaModel, GPT2Model, AutoModel
import torch.nn as nn
import torch
from models.poolings import *

class BaseModel(nn.Module):
    def __init__(self, model_name='electra', hidden_dropout_prob=0.2, num_labels=4):
        super(BaseModel, self).__init__()
        self.model_name = model_name
        self.model = None
        self.get_model()
        self.hidden_size = self.model.config.hidden_size
        self.pooler = MeanPooling()
        self.dropout = nn.Dropout(hidden_dropout_prob)
        self.out = nn.Linear(self.hidden_size * 2, num_labels)
    def get_model(self):
        if self.model_name == 'electra':
            self.model = ElectraModel.from_pretrained('google/electra-small-discriminator', output_hidden_states=True)
        elif self.model_name == 'bert':
            self.model = BertModel.from_pretrained('bert-base-cased')
        elif self.model_name == 'gpt':
            self.model = GPT2Model.from_pretrained('gpt2')
        elif self.model_name == 'electra-base':
            self.model = ElectraModel.from_pretrained('google/electra-base-discriminator')
        elif self.model_name == 'simcsc':
            self.model = AutoModel.from_pretrained('princeton-nlp/sup-simcse-bert-base-uncased')
        elif self.model_name == 'xlnet':
            self.model = AutoModel.from_pretrained('xlnet-base-cased')
    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        hidden_states = outputs.hidden_states
        layer8_output = self.pooler(hidden_states[8], attention_mask)
        layer11_output = self.pooler(hidden_states[11], attention_mask)
        concatenated_output = torch.cat((layer8_output, layer11_output), dim=-1)
        dropout_output = self.dropout(concatenated_output)
        out = self.out(dropout_output)
        return out

class BaseModel(nn.Module):
    def __init__(self, hidden_dropout_prob=0.2, num_labels=4):
        super(BaseModel, self).__init__()
        self.model = ElectraModel.from_pretrained('google/electra-small-discriminator', output_hidden_states=True)
        self.hidden_size = self.model.config.hidden_size
        self.pooler = MeanPooling()
        self.dropout = nn.Dropout(hidden_dropout_prob)
        self.out = nn.Linear(self.hidden_size, num_labels)
    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        hidden_states = outputs.hidden_states
        layer12_output = self.pooler(hidden_states[-1], attention_mask)
        dropout_output = self.dropout(layer12_output)
        out = self.out(dropout_output)
        return out

        