import logging

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from dataloader import TestDataset

class KGEModel(nn.Module):
    def __init__(self, model_name, nentity, nrelation, hidden_dim, gamma,
                double_entity_embedding=False, double_ralation_embedding=False):
        super(KGEModel, self).__init__()
        self.model_name = model_name
        self.nentity = nentity
        self.nrelation = nrelation
        self.hidden_dim = hidden_dim
        self.epsilon = 2.0
        
        # loss function logsigmoid(gamma - score)
        self.gamma = nn.Parameter(
            torch.Tensor([gamma]),
            requires_grad=False
        )

        self.embedding_range = nn.Parameter(
            torch.Tensor([(self.gamma.item() + self.epsilon) / self.hidden_dim]),
            requires_grad=False
        )

        self.entity_dim = hidden_dim * 2 if double_entity_embedding else hidden_dim
        self.relation_dim = hidden_dim * 2 if double_relation_embedding else hidden_dim

        self.entity_embedding = nn.Parameter(torch.zeros(nentity, self.entity_dim))
        nn.init.uniform_(
            tensor=self.entity_embedding,
            a= -self.embedding_range.item(),
            b=self.embedding_range.item()
        )

        self.relation_embedding = nn.Parameter(torc.zeros(nrelation, self.relation_dim))
        nn.init.uniform_(
            tensor=self.relation_embbeding,
            a= -self.embedding_range.item(),
            b=self.embedding_range.item()
        )

        # projection matrix 
        # to get the projection on the hyperplane, e * proj_e * proj_r
        if model_name == 'TransD':
            self.proj_entity_embedding = nn.Parameter(torch.zeros(nentity, self.entity_dim))
            nn.init.uniform_(
                tensor=proj_entity_embedding,
                a= -self.embedding_range.item(),
                b=self.embedding_range.item()
            )

            self.proj_relation_embedding = nn.Parameter(torch.zeros(nrelation, self.relation_dim))
            nn.init.uniform_(
                tensor=self.proj_entity_embedding,
                a= -self.embedding_range.item(),
                b=self.embedding_range.item()
            )

        if model_name == 'pRotatE':
            self.modulus = nn.Parameter(torch.Tensor([[0.5 * self.embedding_range.item()]]))
        
        if model_name not in ['TransE', 'DistMult', 'ComplEx', 'RotatE', 'pRotatE', 'TransD']:
            raise ValueError('model {} not supported'.format(model_name))

        if model_name == 'RotatE' and (not double_entity_embedding or double_relation_embedding):
            raise ValueError('RotatE should use -- double_entity_embedding')

        if model_name == 'ComplEx' and (not double_entity_embedding or not double_ralation_embedding):
            raise ValueError('ComplEx should use --double_entity_embedding and --double_relation_')
    
    def forward(self, sample, mode='single'):
        '''
        Forward function that calculate the score of a batch of triples.
        In the 'single' mode, sample is a batch of triple.
        In the 'head-batch' or 'tail-batch' mode, sample consists two part.
        The first part is usually the positive sample.
        And the second part is the entities in the negative samples.
        Because negative samples and positive samples usually share two elements 
        in their triple ((head, relation) or (relation, tail)).
        '''
        if model == 'single':
            # sample.size() = (batch,3) [:,0] head采样, [:,1] relation采样 [:,2] tail
            batch_size, negative_sample_size = sample.size(0), 1
            # head.size() = (sample_size, 1,entity_dim) 
            head = torch.index_select(
                self.entity_embedding,  # (nentity, entity_dim)
                dim=0,
                index=sample[:, 0]
            ).unsqueeze(1)

            # relation.size() = (sample_size, 1, relation_dim)
            relation = torch.index_select(
                self.relation_embedding,
                dim=0,
                index=sample[:, 1]
            ).unsqueeze(1)

            tail = torch.index_select(
                self.entity_embedding,
                dim=0,
                index=sample[:2]
            ).unsqueeze(1)

            if hasattr(self, 'proj_relation_embedding') and hasattr(self, 'proj_entity_embedding'):
                '''
                calculate the TransD
                '''
                head_t = torch.index_select(
                    self.proj_entity_embedding,
                    dim=0,
                    index=sample[:, 0]
                ).view(batch_size, negative_sample_size, -1)
                
                relation_t = torch.index_select(
                    self.proj_relation_embedding,
                    dim=0,
                    index=sample[:, 1]
                ).unsqueeze(1)

                tail_t = torch.index_select(
                    self.proj_relation_embedding,
                    dim=0,
                    index=sample[:, 2]
                ).unsqueeze(1)

            else:
                head_t = None
                relation_t = None
                tail_t = None
                           
        elif mode == 'head-batch':
            # tail_part contains  (truehead, relation, tail)
            # while head_part only contains the negative head
            tail_part, head_part = sample
            batch_size, negative_sample_size = head_part.size(0), head_part.size(1)

            head = torch.index_select(
                self.entity_embedding,
                dim=0,
                index=head_part.view(-1)
            ).view(batch_size, negative_sample_size, -1)
            
            relation = torch.index_select(
                self.relation_embedding,
                dim=0,
                index=tail_part[:, 1]
            ).unsqueeze(1)

            tail = torch.index_select(
                self.entity_embedding,
                dim=0,
                index=tail_part[:, 2]
            ).unsqueeze(1)

            if hasattr(self, 'proj_entity_embedding') and hasattr(self, 'proj_relation_embedding'):
                head_t = torch.index_select(
                    self.proj_entity_embedding,
                    dim=0,
                    index=head_part.view(-1)
                ).view(batch_size, negative_sample_size, -1)

                relation_t = torch.index_select(
                    self.proj_relation_embedding,
                    dim=0,
                    index=tail_part[:, 1]
                ).unsqueeze(1)

                tail_t = torch.index_select(
                    self.proj_entity_embedding,
                    dim=0,
                    index=tail_part[:, 2]
                ).unsqueeze(1)
            else:
                head_t = None
                relation_t = None
                tail_t = None

        elif mode == 'tail-batch':
            # head_part = (head, relation, true_tail)
            # tail_part = negative_tail.indice
            head_part, tail_part = sample
            batch_size, negative_sample_size = tail_part.size(0), tail_part.size(1)
            
            head = torch.index_select(
                self.entity_embedding,
                dim=0,
                index=head_part[:, 0]
            ).unsqueeze(1)

            relation = torch.index_select(
                self.relation_embedding,
                dim=0,
                index=head_part[:, 1]
            ).unsqueeze(1)

            tail = torch.index_select(
                self.entity_embedding,
                dim=0,
                index=tail_part.view(-1)
            ).view(batch_size, negative_sample_size, -1)

            if hasattr(self, 'proj_entity_embedding') and hasattr(self, 'proj_relation_embedding'):
                head_t = torch.index_select(
                    self.proj_entity_embedding,
                    dim=0,
                    index=head_part[:, 0]
                ).unsqueeze(1)

                relation_t = torch.index_select(
                    self.proj_relation_embedding,
                    dim=0,
                    index=head_part[:, 1]
                ).unsqueeze(1)

                tail_t = torch.index_select(
                    self.proj_entity_embedding,
                    dim=0,
                    index=tail_part.view(-1)
                ).view(batch_size, negative_sample_size, -1)
            else:
                head_t = None
                relation_t = None
                tail_t = None
            
        else:
            raise ValueError(f'mode {mode} not supported')
        
        model_func = {
            'TransE': self.TransE,
            'TransD': self.TransD,
            'DistMult': self.DistMult,
            'ComplEx': self.ComplEx,
            'RotatE': self.RotatE,
            'pRotatE': self.pRotatE
        }

        if self.model_name in model_func:
            score = model_func[self.model_name](head, relation, tail, head_t, relation_t, tail_t, model)
        else:
            raise ValueError(f'model {self.model_name} not supported')

        return score

    def TransE(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        '''
        math:
            score = ||head + relation - tail||1  
            loss = gamma - ||score||1   
        '''
        # propogation mechanism
        if mode == 'head-batch':
            # head.size = (batch, NS_size, -1)
            # (relation - tail).size = int 
            score = head + (relation - tail)
        else:
            score = (head + relation) - tail

        # gamma - N2 of score(dim 2 means the ) 
        # score.size()
        score = self.gamma.item() - torch.norm(score, p=1, dim=2)
        return score

    # calculate the projection vector
    def _transfer(self, e, e_t, r_t):
        return F.normalize(e + (e * e_t).sum(dim=1, keepdim=True) * r_t, 2, -1)
    
    def TransD(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        '''
        math:
            score = ||head_proj, relation, tail_proj||1   
            head_t and relation_t are one column of projection matrix
            imply to show there are 2 different projection way for different entity and relation
            which related to self.proj_entity_embedding and self.proj_relation_embedding 
        '''
        head_proj = self._transfer(head, head_t, relation_t)
        tail_proj = self._transfer(tail, tail_t, relation_t)

        if mode == 'head-batch':
            score = head_proj + (relation - tail_proj)
        else:
            score = (head_proj + relation) - tail_proj
        
        score = self.gamma.item() - torch.norm(score, p=1, dim=2)
        return score
        
    def DistMult(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        '''
        math:
            score = <head, relation, tail>        
        '''
        if mode == 'head-batch':
            score = head * (relation * tail)
        else:
            score = (head * relation) * tail

        score = score.sum(dim=2)
        return score
    
    def ComplEx(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        '''
        Re(<h, r, t`>)
        =   <Re(h), Re(r), Re(t)> 
            + <Re(h), Im(r), Im(t)>
            + <Im(h), Re(r), Im(t)>
            - <Im(h), Im(r), Re(t)>
        = (Re(h), Im(h)) * (Re<r, -t> + Im<r, -t>)
        = (Re(t), Im(t)) * (Re<h, r> + Im<h, r>)
        '''
        re_head, im_head = torch.chunk(head, 2, dim=2)
        re_relation, im_relation = torch.chunk(relation, 2, dim=2)
        re_tail, im_tail = torch.chunk(tail, 2, dim=2)

        if mode == 'head-batch':
            re_score = re_relation * re_tail + im_relation * im_tail
            im_score = re_relation * im_tail - im_relation * re_tail
            score = re_head * re_score + im_head * im_score
        else:
            re_score = re_head * re_relation - im_head * im_relation
            im_score = re_head * im_relation + im_head * re_relation
            score = re_tail * re_score + im_tail * im_score
        
        score = score.sum(dim=2)
        return score


    def RotatE(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        '''
        Complex domain
        score = ||h o r - t||2  where |r| = 1
        '''
        pi = 3.14159265358979323846

        re_head, im_head = torch.chunk(head, 2, dim=2)
        re_tail, im_tail = torch.chunk(tail, 2, dim=2)

        # scale into range (-pi, pi]
        phase_relation =  (relation / self.embedding_range().item() * pi)
        
        re_relation = torch.cos(phase_relation)
        im_relation = torch.sin(phase_relation)

        if mode == 'head-batch':
            re_score = re_relation * re_tail + im_relation * im_tail
            im_score = re_relation * im_tail - im_relation * re_tail
            re_score = re_score - re_head
            im_score = im_score - im_head
        else:
            re_score = re_relation * re_head + im_relation * im_head
            im_score = re_head * im_relation - im_head * re_relation
            re_score = re_score - re_tail
            im_score = im_score - im_tail 

        score = torch.stack([re_score, im_score], dim=0)
        score = score.norm(dim=0)

        score = self.gamma.item() - score.sum(dim=2)
        return score

    # todo
    def pRotatE(self, head, relation, tail, head_t, relation_t, tail_t, mode):
        pi = 3.14159262358979323846

        phase_head = head / (self.embedding_range.item() / pi)
        phase_relation = relation / (self.embedding_range.item() / pi)
        phase_tail = tail / (self.embedding_range.item() / pi)

        if mode == 'head-batch':
            score = phase_head + (phase_relation - phase_tail)
        else:
            score = (phase_head + phase_relation) - phase_tail

        score = torch.sin(score)
        score = torch.abs(score)

        score = self.gamma.item() - score.sum(dim=2) * self.modulus
        return score

    @staticmethod
    def train_step(model, optimizer, train_iterator, args):
        ''' 
        A single train step, apply back_propagation and return the loss
        '''

        # model(sample, model) = forward(sample, model)
        
        model.train()

        optimizer.zeros_grad()
        
        #  positive_sample, negative_sample size()?
        # 在这个地方放入KGE信息 
        positive_sample, negative_sample, subsampling_weight, mode = next(train_iterator)

        if args.cuda:
            positive_sample = positive_sample.cuda()
            negative_sample = negative_sample.cuda()
            subsampling_weight = subsampling_weight.cuda()

        # negative sample size
        negative_score = model((positive_sample, negative_sample), mode=mode)

        # adv_RW
        # Loss = positive_score + adv * negative_score
        if args.negative_adversarial_sampling:
            negative_score = (F.softmax(negative_score * args.adversarial_temperature, dim=1).detach()
                * F.logsigmoid(-negative_score)).sum(dim=1)

        else:
            negative_score = F.logsigmoid(-negative_score).mean(dim=1)

        # single mode calculate positive_score
        positive_score = model(positive_sample)   

        positive_score = F.logsigmoid(positive_score).squeeze(dim=1)

        if args.uni_weight:
            positive_sample_loss = -positive_score.mean()
            negative_sample_loss = -negative_score.mean()
        else:
            positive_sample_loss = -(subsampling_weight * positive_score).sum() / subsampling_weight.sum()
            negative_sample_loss = -(subsampling_weight * negative_score).sum() / subsampling_weight.sum()

        loss = (positive_sample_loss + negative_sample_loss) / 2
        
        if args.regularization != 0.0:
            # Use L3 regularization for ComplEx and DistMult
            regularization = args.regularization * (
                model.entity_embedding.norm(p=3) ** 3 +
                model.relation_embbeding.norm(p=3) ** 3
            )
            loss = loss + regularization
            regularization_log = {'regularization': regularization.item()}
        else:
            regularization_log = {}

        loss.backward()

        optimizer.step()

        log = {
            **regularization_log,
            'positive_sample_loss': positive_sample_loss.item(),
            'negative_sample_loss': negative_sample_loss.item(),
            'loss': loss.item()
        }

        return log

    # towriter
    @staticmethod
    def test_step(model, test_triples, all_true_triples, args):
        '''
        evaluate the model on the test
        '''
        model.eval()

        test_dataloader_head = DataLoader(
            TestDataset(
                test_triples,
                all_true_triples,
                args.nentity,
                args.nrelation,
                'tail-batch'
            ),
            batch_size=args.test_batch_size,
            num_workers=max(1, args.cpu_num // 2),
            collate_fn=TestDataset.collate_fn
        )

        test_dataset_list = [test_dataloader_head, test_dataloader_tail]

        log = []

        step = 0
        total_step = sum([len(dataset) for dataset in test_dataset_list])

        with torch.no_grad():
            for test_dataset in test_dataset_list:
                for postive_sample, negative_sample, filter_bias, mode in test_daatset:
                    if args.cuda:
                        postive_sample = postive_sample.cuda()
                        negative_sample = negative_sample.cuda()
                        filter_bias = filter_bias.cuda()

                    batch_size = postive_sample.size(0)

                    score = model((postive_sample, negative_sample), mode)
                    score += filter_bias

                    argsort = torch.argsort(score, dim=1, descending=True)

                    if mode == 'head-batch':
                        positive_arg = positive_sample[:, 0]
                    elif mode == 'tail-batch':
                        positive_arg = positive_sample[:, 2]
                    else:
                        raise ValueError('mode %s not supported' % mode)

                    for i in range(batch_size):
                        ranking = (argsort[i,:] == postive_arg[i]).nonzero()
                        
                        assert ranking.size(0) == 1
                        
                        # ranking + 1 is the true ranking used in evaluation metrics
                        ranking = 1 + ranking.item()
                        logs.append({
                            'MRR': 1.0 / ranking,
                            'MR': float(ranking),
                            'HITS@1': 1.0 if ranking <= 1 else 0.0,
                            'HITS@3': 1.0 if ranking <= 3 else 0.0,
                            'HITS@10': 1.0 if ranking <= 10 else 0.0,
                        })
                    
                    if step % args.test_log_steps == 0:
                        logging.info('Evaluating the model... (%d/%d)' % (step, total_steps))
                    
                    step += 1

        metrics = {}
        for metric in logs[0].keys():
            metrics[metric] = sum([log[metric] for log in logs]) / len(logs)

        return metrics



def main():
    # sample = torch.randint(0, 10, size=(4, 3)).long()
    # print(sample)
    # a = torch.randn(10, 4)
    # print(a)
    # b = torch.index_select(
    #     input=a,
    #     dim=0,
    #     index=sample[:,0]
    # ).unsqueeze(1)
    # print(b.size())

    sample = torch.ones(3, 4)
    sample = sample.view(-1)
    print(sample)

if __name__ == "__main__":
    main()